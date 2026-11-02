"""Autenticación, 2FA, gestión de usuarios y guards con autorización en servidor."""

import io
import secrets
import time
import pyotp
import qrcode
from gsreview.configuration import BRAND
from sqlalchemy import select, func, and_
from gsreview.domain.rules import (
    AccessDenied,
    ValidationError,
    PERMISSIONS,
    Role,
    password_policy,
    username_policy,
)
from gsreview.infrastructure import store as db
from gsreview.infrastructure.security import PASSWORDS, DUMMY_HASH, matches, digest

GENERIC = "No fue posible validar el acceso. Comprueba tus datos o espera antes de reintentar."


class AuthService:
    def __init__(self, store, cipher, clock=time.time):
        self.store, self.cipher, self.clock = store, cipher, clock

    def _audit(self, c, actor, action, object_id="", detail=None):
        self.store.audit(c, actor, action, object_id, detail, self.clock())

    def _user(self, c, user_id):
        return c.execute(select(db.users).where(db.users.c.id == user_id)).mappings().first()

    def _session(self, c, token, kind="session"):
        s = (
            c.execute(select(db.sessions).where(db.sessions.c.hash == digest(token)))
            .mappings()
            .first()
        )
        if not s or s["kind"] != kind or s["expires_at"] <= self.clock():
            raise AccessDenied("La sesión o verificación expiró. Inicia sesión nuevamente.")
        user = self._user(c, s["user_id"])
        if not user or not user["active"]:
            raise AccessDenied(GENERIC)
        return user

    def _token(self, c, user_id, kind):
        raw = secrets.token_urlsafe(32)
        now = self.clock()
        c.execute(
            db.sessions.insert().values(
                hash=digest(raw),
                user_id=user_id,
                kind=kind,
                created_at=now,
                last_seen=now,
                expires_at=now + (900 if kind == "session" else 300),
            )
        )
        return raw

    def _new_user(self, c, username, display_name, password, role, force_change=False):
        username_policy(username)
        password_policy(username, password)
        if role not in PERMISSIONS or not display_name.strip() or len(display_name) > 100:
            raise ValidationError("Rol o nombre visible no válido.")
        if c.scalar(select(db.users.c.id).where(db.users.c.username == username)):
            raise ValidationError("No se puede crear esa cuenta.")
        user_id, now = db.uid(), self.clock()
        h = PASSWORDS.hash(password)
        c.execute(
            db.users.insert().values(
                id=user_id,
                username=username,
                display_name=display_name.strip(),
                role=role,
                password_hash=h,
                active=True,
                totp_cipher=self.cipher.encrypt(pyotp.random_base32()),
                totp_enabled=False,
                last_totp_step=-1,
                failures=0,
                blocked_until=0,
                next_attempt=0,
                force_change=force_change,
                created_at=now,
            )
        )
        c.execute(
            db.password_history.insert().values(
                id=db.uid(), user_id=user_id, hash=h, created_at=now
            )
        )
        return user_id

    def bootstrap(self, username, display_name, password):
        with self.store.tx() as c:
            if c.scalar(select(func.count()).select_from(db.users)):
                raise AccessDenied("La configuración inicial ya fue realizada.")
            user_id = self._new_user(
                c, username.lower().strip(), display_name, password, Role.ADMIN.value
            )
            self._audit(
                c, user_id, "user_created", user_id, {"role": Role.ADMIN.value, "bootstrap": True}
            )
            return self._token(c, user_id, "enroll")

    def _failed(self, c, user, stage, username):
        now = self.clock()
        c.execute(
            db.login_attempts.insert().values(
                id=db.uid(), username=username, stage=stage, success=False, timestamp=now
            )
        )
        actor = user["id"] if user else None
        self._audit(c, actor, "login_failed", "", {"stage": stage})
        if user:
            failures = user["failures"] + 1
            c.execute(
                db.users.update()
                .where(db.users.c.id == user["id"])
                .values(
                    failures=failures,
                    blocked_until=now + 900 if failures >= 5 else 0,
                    next_attempt=now + min(2 ** (failures - 1), 30),
                )
            )
            if failures >= 5:
                self._audit(c, actor, "account_locked", actor)

    def password_step(self, username, password):
        username, error, token = username.lower().strip(), False, None
        with self.store.tx() as c:
            user = (
                c.execute(select(db.users).where(db.users.c.username == username))
                .mappings()
                .first()
            )
            good = matches(user["password_hash"] if user else DUMMY_HASH, password)
            # Cuenta desconocida: aplica también un presupuesto por identificador.
            recent = c.scalar(
                select(func.count())
                .select_from(db.login_attempts)
                .where(
                    and_(
                        db.login_attempts.c.username == username,
                        db.login_attempts.c.success.is_(False),
                        db.login_attempts.c.timestamp > self.clock() - 900,
                    )
                )
            )
            ready = (
                user
                and user["active"]
                and user["blocked_until"] <= self.clock()
                and user["next_attempt"] <= self.clock()
            )
            if not good or not ready or (not user and recent >= 5):
                # Reintentos antes de la espera se auditan, pero no prolongan el bloqueo.
                if user and (
                    user["blocked_until"] > self.clock() or user["next_attempt"] > self.clock()
                ):
                    self._audit(c, user["id"], "login_throttled")
                else:
                    self._failed(c, user, "password", username)
                error = True
            else:
                c.execute(
                    db.sessions.delete().where(
                        and_(db.sessions.c.user_id == user["id"], db.sessions.c.kind != "session")
                    )
                )
                token = self._token(
                    c, user["id"], "challenge" if user["totp_enabled"] else "enroll"
                )
                self._audit(c, user["id"], "password_verified")
        if error:
            raise AccessDenied(GENERIC)
        return token, "challenge" if user["totp_enabled"] else "enroll"

    def enrollment(self, token):
        with self.store.tx() as c:
            user = self._session(c, token, "enroll")
            if user["totp_enabled"]:
                raise AccessDenied(GENERIC)
            secret = self.cipher.decrypt(user["totp_cipher"])
            uri = pyotp.TOTP(secret).provisioning_uri(user["username"], issuer_name=BRAND["name"])
        image = qrcode.make(uri)
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue(), secret

    def _totp_step(self, user, code):
        if len(code) != 6 or not code.isdigit():
            return None
        otp = pyotp.TOTP(self.cipher.decrypt(user["totp_cipher"]))
        step = int(self.clock() // 30)
        for candidate in (step, step - 1, step + 1):
            if candidate > user["last_totp_step"] and secrets.compare_digest(
                otp.at(candidate * 30), code
            ):
                return candidate
        return None

    def _recovery(self, c, user_id):
        codes = [secrets.token_hex(10).upper() for _ in range(10)]
        c.execute(db.recovery_codes.delete().where(db.recovery_codes.c.user_id == user_id))
        c.execute(
            db.recovery_codes.insert(),
            [{"hash": digest(code), "user_id": user_id} for code in codes],
        )
        return codes

    def second_step(self, token, code, enroll=False, recovery=False):
        error, codes, session = False, [], None
        with self.store.tx() as c:
            user = self._session(c, token, "enroll" if enroll else "challenge")
            if user["blocked_until"] > self.clock() or user["next_attempt"] > self.clock():
                self._audit(c, user["id"], "login_throttled")
                error = True
            else:
                step = self._totp_step(user, code) if not recovery else None
                recovered = False
                if recovery and not enroll:
                    item = (
                        c.execute(
                            select(db.recovery_codes).where(
                                and_(
                                    db.recovery_codes.c.hash == digest(code.strip().upper()),
                                    db.recovery_codes.c.user_id == user["id"],
                                    db.recovery_codes.c.used_at.is_(None),
                                )
                            )
                        )
                        .mappings()
                        .first()
                    )
                    if item:
                        c.execute(
                            db.recovery_codes.update()
                            .where(db.recovery_codes.c.hash == item["hash"])
                            .values(used_at=self.clock())
                        )
                        recovered = True
                        self._audit(c, user["id"], "recovery_used")
                if step is None and not recovered:
                    self._failed(c, user, "totp", user["username"])
                    error = True
                else:
                    values = {
                        "failures": 0,
                        "blocked_until": 0,
                        "next_attempt": 0,
                        "last_login": self.clock(),
                    }
                    if step is not None:
                        values["last_totp_step"] = step
                    if enroll:
                        values["totp_enabled"] = True
                        codes = self._recovery(c, user["id"])
                        self._audit(c, user["id"], "totp_activated")
                    c.execute(db.users.update().where(db.users.c.id == user["id"]).values(**values))
                    c.execute(db.sessions.delete().where(db.sessions.c.hash == digest(token)))
                    session = self._token(c, user["id"], "session")
                    c.execute(
                        db.login_attempts.insert().values(
                            id=db.uid(),
                            username=user["username"],
                            stage="totp",
                            success=True,
                            timestamp=self.clock(),
                        )
                    )
                    self._audit(c, user["id"], "login_success")
        if error:
            raise AccessDenied(GENERIC)
        return session, codes

    def authorize(self, token, permission="read"):
        with self.store.tx() as c:
            user = self.guard(c, token, permission)
            c.execute(
                db.sessions.update()
                .where(db.sessions.c.hash == digest(token))
                .values(last_seen=self.clock(), expires_at=self.clock() + 900)
            )
            return {k: user[k] for k in ("id", "username", "display_name", "role", "force_change")}

    def guard(self, c, token, permission):
        user = self._session(c, token)
        if permission not in PERMISSIONS[user["role"]] or (
            user["force_change"] and permission != "profile"
        ):
            raise AccessDenied("Acceso no autorizado o cambio de contraseña pendiente.")
        return user

    def logout(self, token):
        with self.store.tx() as c:
            user = self._session(c, token)
            c.execute(db.sessions.delete().where(db.sessions.c.hash == digest(token)))
            self._audit(c, user["id"], "logout")

    def create_user(self, token, username, name, password, role):
        actor = self.authorize(token, "users")
        with self.store.tx() as c:
            self.guard(c, token, "users")
            user_id = self._new_user(c, username.lower().strip(), name, password, role, True)
            self._audit(c, actor["id"], "user_created", user_id, {"role": role})
            return user_id

    def user_action(self, token, user_id, action, value=None):
        actor = self.authorize(token, "users")
        allowed = {"active", "role", "unlock", "force_change", "reset_totp", "revoke_sessions"}
        if action not in allowed or (action == "role" and value not in PERMISSIONS):
            raise ValidationError("Acción no admitida.")
        with self.store.tx() as c:
            self.guard(c, token, "users")
            user = self._user(c, user_id)
            if not user:
                raise ValidationError("Cuenta no disponible.")
            if (
                user["active"]
                and user["role"] == Role.ADMIN.value
                and (
                    (action == "active" and value is False)
                    or (action == "role" and value != Role.ADMIN.value)
                )
            ):
                count = c.scalar(
                    select(func.count())
                    .select_from(db.users)
                    .where(and_(db.users.c.active.is_(True), db.users.c.role == Role.ADMIN.value))
                )
                if count <= 1:
                    raise ValidationError("Debe conservarse al menos un administrador activo.")
            updates = {}
            if action in ("active", "role"):
                updates[action] = value
            if action == "unlock":
                updates.update(failures=0, blocked_until=0, next_attempt=0)
            if action == "force_change":
                updates["force_change"] = True
            if action == "reset_totp":
                updates.update(
                    totp_cipher=self.cipher.encrypt(pyotp.random_base32()),
                    totp_enabled=False,
                    last_totp_step=-1,
                )
                c.execute(db.recovery_codes.delete().where(db.recovery_codes.c.user_id == user_id))
            if updates:
                c.execute(db.users.update().where(db.users.c.id == user_id).values(**updates))
            if action != "unlock":
                c.execute(db.sessions.delete().where(db.sessions.c.user_id == user_id))
            self._audit(
                c,
                actor["id"],
                "user_" + action,
                user_id,
                {"value": value} if action in ("role", "active") else {},
            )

    def change_password(self, token, old, new):
        actor = self.authorize(token, "profile")
        password_policy(actor["username"], new)
        with self.store.tx() as c:
            self.guard(c, token, "profile")
            user = self._user(c, actor["id"])
            if not matches(user["password_hash"], old):
                raise AccessDenied(GENERIC)
            history = c.execute(
                select(db.password_history.c.hash)
                .where(db.password_history.c.user_id == user["id"])
                .order_by(db.password_history.c.created_at.desc())
                .limit(5)
            ).scalars()
            if any(matches(h, new) for h in history):
                raise ValidationError("No reutilices ninguna de tus últimas cinco contraseñas.")
            h = PASSWORDS.hash(new)
            c.execute(
                db.users.update()
                .where(db.users.c.id == user["id"])
                .values(password_hash=h, force_change=False)
            )
            c.execute(
                db.password_history.insert().values(
                    id=db.uid(), user_id=user["id"], hash=h, created_at=self.clock()
                )
            )
            c.execute(db.sessions.delete().where(db.sessions.c.user_id == user["id"]))
            self._audit(c, user["id"], "password_changed")

    def regenerate_recovery(self, token, password, otp):
        actor = self.authorize(token, "profile")
        with self.store.tx() as c:
            self.guard(c, token, "profile")
            user = self._user(c, actor["id"])
            step = self._totp_step(user, otp)
            if not matches(user["password_hash"], password) or step is None:
                raise AccessDenied(GENERIC)
            c.execute(
                db.users.update().where(db.users.c.id == user["id"]).values(last_totp_step=step)
            )
            codes = self._recovery(c, user["id"])
            self._audit(c, user["id"], "recovery_regenerated")
            return codes

    def safe_users(self, token):
        self.authorize(token, "users")
        fields = (
            "id",
            "username",
            "display_name",
            "role",
            "active",
            "totp_enabled",
            "failures",
            "blocked_until",
            "last_login",
        )
        return [{k: r[k] for k in fields} for r in self.store.list("users")]

    def safe_sessions(self, token):
        self.authorize(token, "users")
        return [
            {k: r[k] for k in ("user_id", "kind", "created_at", "last_seen", "expires_at")}
            for r in self.store.list("sessions")
            if r["expires_at"] > self.clock()
        ]
