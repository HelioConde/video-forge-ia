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
