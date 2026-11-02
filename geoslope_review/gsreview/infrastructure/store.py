"""Persistencia SQLAlchemy, repositorio transaccional y auditoría append-only."""

import json
import os
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    create_engine,
    event,
    select,
    func,
    text,
)

metadata = MetaData()


def table(name, *columns):
    return Table(name, metadata, *columns)


roles = table("roles", Column("name", String, primary_key=True))
users = table(
    "users",
    Column("id", String, primary_key=True),
    Column("username", String, unique=True, nullable=False),
    Column("display_name", String, nullable=False),
    Column("role", ForeignKey("roles.name"), nullable=False),
    Column("password_hash", String, nullable=False),
    Column("active", Boolean, nullable=False),
    Column("totp_cipher", String, nullable=False),
    Column("totp_enabled", Boolean, nullable=False),
    Column("last_totp_step", Integer, nullable=False),
    Column("failures", Integer, nullable=False),
    Column("blocked_until", Float, nullable=False),
    Column("next_attempt", Float, nullable=False),
    Column("force_change", Boolean, nullable=False),
    Column("last_login", Float),
    Column("created_at", Float, nullable=False),
)
password_history = table(
    "password_history",
    Column("id", String, primary_key=True),
    Column("user_id", ForeignKey("users.id"), nullable=False, index=True),
    Column("hash", String, nullable=False),
    Column("created_at", Float, nullable=False),
)
recovery_codes = table(
    "recovery_codes",
    Column("hash", String, primary_key=True),
    Column("user_id", ForeignKey("users.id"), nullable=False, index=True),
    Column("used_at", Float),
)
sessions = table(
    "sessions",
    Column("hash", String, primary_key=True),
    Column("user_id", ForeignKey("users.id"), nullable=False, index=True),
    Column("kind", String, nullable=False),
    Column("created_at", Float, nullable=False),
    Column("last_seen", Float, nullable=False),
    Column("expires_at", Float, nullable=False),
)
login_attempts = table(
    "login_attempts",
    Column("id", String, primary_key=True),
    Column("username", String, index=True),
    Column("stage", String, nullable=False),
    Column("success", Boolean, nullable=False),
    Column("timestamp", Float),
)
app_metadata = table(
    "app_metadata", Column("key", String, primary_key=True), Column("value", String, nullable=False)
)
data_imports = table(
    "data_imports",
    Column("id", String, primary_key=True),
    Column("manifest_hash", String, nullable=False),
    Column("created_at", Float, nullable=False),
    Column("rows", Integer, nullable=False),
)
episodes = table(
    "episodes",
    Column("id", String, primary_key=True),
    Column("prism_id", String, index=True, nullable=False),
    Column("payload", String, nullable=False),
)
episode_reviews = table(
    "episode_reviews",
    Column("episode_id", ForeignKey("episodes.id"), primary_key=True),
    Column("version", Integer, nullable=False),
    Column("payload", String, nullable=False),
    Column("reviewer", ForeignKey("users.id")),
    Column("updated_at", Float),
)
review_history = table(
    "review_history",
    Column("id", String, primary_key=True),
    Column("episode_id", ForeignKey("episodes.id"), nullable=False, index=True),
    Column("version", Integer, nullable=False),
    Column("payload", String, nullable=False),
    Column("reviewer", ForeignKey("users.id"), nullable=False),
    Column("timestamp", Float, nullable=False),
)
audit_log = table(
    "audit_log",
    Column("id", String, primary_key=True),
    Column("actor", String),
    Column("action", String, nullable=False, index=True),
    Column("object_id", String),
    Column("detail", String, nullable=False),
    Column("timestamp", Float, nullable=False),
)
report_history = table(
    "report_history",
    Column("id", String, primary_key=True),
    Column("actor", ForeignKey("users.id")),
    Column("scope", String),
    Column("format", String),
    Column("sha256", String),
    Column("timestamp", Float),
)
artifact_integrity = table(
    "artifact_integrity",
    Column("path", String, primary_key=True),
    Column("sha256", String),
    Column("verified_at", Float),
)
backup_history = table(
    "backup_history",
    Column("id", String, primary_key=True),
    Column("filename", String),
    Column("sha256", String),
    Column("timestamp", Float),
)


def uid():
    return uuid.uuid4().hex


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.engine = create_engine(
            "sqlite:///" + str(self.path), connect_args={"check_same_thread": False, "timeout": 20}
        )

        @event.listens_for(self.engine, "connect")
        def pragmas(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

        metadata.create_all(self.engine)
        with self.tx() as c:
            for role in ("administrador", "ingeniero"):
                c.execute(text("INSERT OR IGNORE INTO roles(name) VALUES (:role)"), {"role": role})
            c.execute(
                text("INSERT OR IGNORE INTO app_metadata(key,value) VALUES ('schema_version','1')")
            )
            for name, verb in [
                ("immutable_audit_update", "UPDATE"),
                ("immutable_audit_delete", "DELETE"),
            ]:
                c.execute(
                    text(
                        f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {verb} ON audit_log BEGIN SELECT RAISE(ABORT,'Audit is append-only'); END"
                    )
                )
        if os.name != "nt":
            self.path.chmod(0o600)

    @contextmanager
    def tx(self):
        # BEGIN IMMEDIATE serializa decisiones sensibles incluso entre procesos.
        with self.lock, self.engine.connect() as c:
            c.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield c
                c.commit()
            except Exception:
                c.rollback()
                raise

    def list(self, table_name):
        with self.engine.connect() as c:
            return [dict(r) for r in c.execute(select(metadata.tables[table_name])).mappings()]

    def user_count(self):
        with self.engine.connect() as c:
            return c.scalar(select(func.count()).select_from(users))

    @staticmethod
    def audit(c, actor, action, object_id="", detail=None, now=0):
        c.execute(
            audit_log.insert().values(
                id=uid(),
                actor=actor,
                action=action,
                object_id=object_id,
                detail=json.dumps(detail or {}, ensure_ascii=False),
                timestamp=now,
            )
        )
