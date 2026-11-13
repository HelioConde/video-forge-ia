"""Antirrepetição pessimista: inventário completo, reservas e similaridade textual.

Não afirmar unicidade sem histórico integral do canal. Uma mudança de título,
um reupload e um vídeo privado podem representar o mesmo assunto.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

class DuplicateTopic(ValueError):
    pass

def norm(text: str) -> str:
    if not isinstance(text, str):
        return ""
    value = unicodedata.normalize("NFKD", text).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))

def editorial_fingerprint(item: dict) -> str:
    if item.get("topic_key"):
        return norm(item["topic_key"])
    return norm(" ".join(str(item.get(k, "")) for k in ("anime", "assunto", "abordagem")))

# Remove only common framing words, never character or conflict identifiers.
# Similarity checks are conservative and channel-scoped, not proof of
# semantic originality. The human/Subgerente gate still audits the full story.
_GENERIC = frozenset("""
    a as o os um uma uns umas de da do das dos e em na no nas nos para por
    com sem que como porque pq qual quais foi era ser sao ter tem tinha ao aos
    isto isso essa esse esta este este esta mais menos muito tudo todos toda
    verdade verdadeiro verdadeira segredo secreto misterio curiosidade
    curiosidades incrivel explicacao explicado analise anime animes short
    shorts episodio parte historia personagem personagens personagem principal
    motivacao motivo poder poderes novo nova real completo chocante
    consegue conseguiu podia pode muda mudou mudar mesmo mesma
""".split())


def _topic_terms(value: str, *, anime: str) -> set[str]:
    series_words = set(norm(anime).split())
    return {token for token in norm(value).split()
            if len(token) >= 4 and token not in _GENERIC
            and token not in series_words}


def _related_published_theme(candidate: dict, other_title: str) -> bool:
    """Catch related character/concept angles that title similarity misses.

    More than one distinctive token implies topic overlap even if a title
    was rewritten. On an explicitly named same series, one shared unique
    character/concept may be enough. This is a conservative review blocker.
    """
    anime = candidate.get("anime", "")
    series = norm(anime)
    if not series:
        return False
    other_norm = norm(other_title)
    left = _topic_terms(" ".join(str(candidate.get(k, "")) for k in
                                 ("titulo_provisorio", "assunto", "abordagem")),
                        anime=anime)
    right = _topic_terms(other_title, anime=anime)
    common = left & right
    if not common or not left or not right:
        return False
    named_series = (" " + series + " ") in (" " + other_norm + " ")
    if named_series and len(common) >= 1:
        return True
    return len(common) >= 2 and len(common) / min(len(left), len(right)) >= .5


def assert_unique(candidate: dict, *, inventory: dict, reservations: dict,
                  extra_titles: tuple[str, ...] = ()) -> None:
    if not inventory.get("history_complete") or inventory.get("count") != len(inventory.get("videos", [])):
        raise DuplicateTopic("HISTORICO_YOUTUBE_INCOMPLETO")
    if reservations.get("schema") != "videoforge/channel-topic-reservations/v1":
        raise DuplicateTopic("RESERVAS_INVALIDAS")
    if reservations.get("channel_id") != inventory.get("channel_id"):
        raise DuplicateTopic("RESERVAS_OUTRO_CANAL")
    if candidate.get("channel_id") != inventory.get("channel_id"):
        raise DuplicateTopic("PAUTA_OUTRO_CANAL")
    fingerprint = editorial_fingerprint(candidate)
    title = norm(candidate.get("titulo_provisorio", ""))
    if len(fingerprint) < 12 or len(title) < 12:
        raise DuplicateTopic("PAUTA_INSUFICIENTE_PARA_ANTIRREPETICAO")
    existing = reservations.get("entries") or []
    if not isinstance(existing, list):
        raise DuplicateTopic("RESERVAS_INVALIDAS")
    for prior in existing:
        if not isinstance(prior, dict):
            raise DuplicateTopic("RESERVAS_INVALIDAS")
        same_topic = editorial_fingerprint(prior)
        if fingerprint == same_topic:
            raise DuplicateTopic("PAUTA_JA_RESERVADA")
        if same_topic and SequenceMatcher(None, fingerprint, same_topic).ratio() >= .88:
            raise DuplicateTopic("PAUTA_SIMILAR_JA_RESERVADA")
        other_title = norm(prior.get("titulo_provisorio", ""))
        if other_title and (title == other_title or SequenceMatcher(None, title, other_title).ratio() >= .85):
            raise DuplicateTopic("TITULO_RESERVADO_OU_SIMILAR")
        if other_title and _related_published_theme(candidate, other_title):
            raise DuplicateTopic("TEMA_RELACIONADO_JA_RESERVADO")

    for prior in list(inventory["videos"]) + [{"title": x} for x in extra_titles]:
        other_title = norm(prior.get("title") or prior.get("titulo_provisorio") or "")
        if not other_title or other_title in {"private video", "deleted video", "video privado"}:
            raise DuplicateTopic("TITULO_EXISTENTE_INACESSIVEL")
        if title == other_title or SequenceMatcher(None, title, other_title).ratio() >= .83:
            raise DuplicateTopic("TEMA_PUBLICADO_OU_MUITO_PARECIDO")
        # Sem classificação anterior de anime/assunto, aproximar o tópico inteiro
        # ao título publicado como segunda barreira contra reformulações.
        if len(other_title) > 12 and SequenceMatcher(None, fingerprint, other_title).ratio() >= .82:
            raise DuplicateTopic("PAUTA_SEMELHANTE_A_VIDEO_EXISTENTE")
        if _related_published_theme(candidate, other_title):
            raise DuplicateTopic("TEMA_RELACIONADO_JA_PUBLICADO")
