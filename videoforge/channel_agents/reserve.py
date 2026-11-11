"""Reserva local transacional de pauta — exige armazenamento DURÁVEL do backend.

Este arquivo de reservas NÃO deve ser gravado automaticamente no site público
nem a partir de um runner efêmero sem persistência entre execuções.
A validação ocorre novamente DENTRO do lock antes de qualquer produção.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
import json
import os

from .dedup import assert_unique, editorial_fingerprint, DuplicateTopic


class TopicReservationError(RuntimeError):
    pass


@contextmanager
def _exclusive_lock(target: Path):
    lock = target.with_suffix(target.suffix + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise TopicReservationError("CHANNEL_EDITORIAL_LOCKED") from None
    try:
        with os.fdopen(fd, "w") as f:
            f.write("locked\n")
        yield
    finally:
        lock.unlink(missing_ok=True)


def reserve_topic(*, candidate: dict, inventory: dict,
                  ledger_path: Path, persist_approved: bool) -> dict:
    if not persist_approved:
        raise TopicReservationError("PERSISTENT_RESERVATION_NOT_AUTHORIZED")
    ledger_path = Path(ledger_path)
    if ledger_path.is_symlink() or not ledger_path.is_file():
        raise TopicReservationError("PERSISTENT_LEDGER_UNAVAILABLE")
    with _exclusive_lock(ledger_path):
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        assert_unique(candidate, inventory=inventory, reservations=ledger)
        for entry in ledger["entries"]:
            if entry.get("id") == candidate.get("id"):
                raise DuplicateTopic("RESERVATION_ID_ALREADY_USED")
        entry = {
            "id": candidate["id"],
            "channel_id": candidate["channel_id"],
            "topic_key": editorial_fingerprint(candidate),
            "anime": candidate["anime"],
            "assunto": candidate["assunto"],
            "abordagem": candidate["abordagem"],
            "titulo_provisorio": candidate["titulo_provisorio"],
            "status": "reserved",
            "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        ledger["entries"].append(entry)
        # Escrita durável e troca atômica: não perde o arquivo original.
        temp_name = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=ledger_path.parent,
                                    prefix=".channel-reservation-", delete=False) as fd:
                temp_name = fd.name
                json.dump(ledger, fd, ensure_ascii=False, indent=2)
                fd.write("\n")
                fd.flush()
                os.fsync(fd.fileno())
            os.replace(temp_name, ledger_path)
        finally:
            if temp_name:
                Path(temp_name).unlink(missing_ok=True)
        return entry
