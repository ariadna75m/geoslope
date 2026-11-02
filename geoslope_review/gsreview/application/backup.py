"""Snapshots cifrados, restauración transaccional y conservación de auditoría."""

import hashlib
import json
from pathlib import Path
from sqlalchemy import select
from cryptography.fernet import InvalidToken
from gsreview.domain.rules import ValidationError
from gsreview.infrastructure import store as db


class BackupService:
    def __init__(self, auth, reader, directory):
        self.auth, self.reader, self.store = auth, reader, auth.store
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def create(self, token):
        actor = self.auth.authorize(token, "backup")
        self.reader.verify()
        with self.store.tx() as c:
            self.auth.guard(c, token, "backup")
            snapshot = {
                t.name: [dict(r) for r in c.execute(select(t)).mappings()]
                for t in db.metadata.sorted_tables
                if t.name != "sessions"
            }
            payload = json.dumps(
                {"schema": 1, "manifest": self.reader.manifest, "tables": snapshot},
                ensure_ascii=False,
            )
            ciphertext = self.auth.cipher.encrypt(payload).encode()
            name = "backup_" + db.uid() + ".gsbackup"
            path = self.directory / name
            path.write_bytes(ciphertext)
            path.chmod(0o600)
            c.execute(
                db.backup_history.insert().values(
                    id=db.uid(),
                    filename=name,
                    sha256=hashlib.sha256(ciphertext).hexdigest(),
                    timestamp=self.auth.clock(),
                )
            )
            self.auth._audit(c, actor["id"], "backup_created", name)
        return path

    def list(self, token):
        self.auth.authorize(token, "backup")
        return sorted(self.directory.glob("*.gsbackup"))

    def restore(self, token, content):
        actor = self.auth.authorize(token, "backup")
        try:
            payload = json.loads(self.auth.cipher.decrypt(content.decode()))
        except (InvalidToken, ValueError, UnicodeError) as e:
            raise ValidationError("Copia incompatible o clave local diferente.") from e
        expected = set(db.metadata.tables) - {"sessions"}
        tables = payload.get("tables", {})
        if (
            payload.get("schema") != 1
            or payload.get("manifest") != self.reader.manifest
            or set(tables) != expected
        ):
            raise ValidationError("Esquema o artefactos de la copia incompatibles.")
        if not any(
            u["active"] and u["role"] == "administrador" and u["totp_enabled"]
            for u in tables["users"]
        ):
            raise ValidationError("La copia necesita un administrador activo con doble factor.")
        for name, records in tables.items():
            columns = set(db.metadata.tables[name].c.keys())
            if any(set(r) != columns for r in records):
                raise ValidationError("Columnas incompatibles en la copia.")
        self.reader.verify()
        # La copia de seguridad anterior a restaurar se conserva en el mismo directorio.
        self.create(token)
        with self.store.tx() as c:
            self.auth.guard(c, token, "backup")
            self.auth._audit(c, actor["id"], "restore_started")
            existing_audit = set(c.execute(select(db.audit_log.c.id)).scalars())
            c.execute(db.sessions.delete())
            for t in reversed(db.metadata.sorted_tables):
                if t.name not in ("audit_log", "sessions"):
                    c.execute(t.delete())
            for t in db.metadata.sorted_tables:
                if t.name == "sessions":
                    continue
                records = tables[t.name]
                if t.name == "audit_log":
                    records = [r for r in records if r["id"] not in existing_audit]
                if records:
                    c.execute(t.insert(), records)
            self.auth._audit(c, actor["id"], "backup_restored", detail={"sessions_revoked": True})
