import json
import pyotp
import pytest
from gsreview.domain.rules import AccessDenied, ValidationError, password_policy
from gsreview.infrastructure import store as db
from gsreview.infrastructure.security import digest
from conftest import engineer


def test_argon2_cipher_hashes_and_no_plaintext_secrets(app):
    user = app.store.list("users")[0]
    assert user["password_hash"].startswith("$argon2id$")
    assert app.test_secret not in user["totp_cipher"]
    assert app.cipher.decrypt(user["totp_cipher"]) == app.test_secret
    encoded = json.dumps({t: app.store.list(t) for t in db.metadata.tables})
    assert app.test_password not in encoded and app.test_admin not in encoded
    assert not any(code in encoded for code in app.test_codes)


@pytest.mark.parametrize(
    "password",
    [
        "short",
        "verylongpassword123!",
        "VeryLongPassword!",
        "VERYLONGPASSWORD123!",
        "Testadmin!123456",
    ],
)
def test_password_policy_rejects_invalid(password):
    with pytest.raises(ValidationError):
        password_policy("testadmin", password)


def test_wrong_password_and_unknown_user_have_generic_error(app):
    messages = []
    for username in ("testadmin", "missing"):
        with pytest.raises(AccessDenied) as e:
            app.auth.password_step(username, "Incorrect!12345678")
        messages.append(str(e.value))
    assert messages[0] == messages[1]


def test_five_attempt_lock_progressive_wait_and_unlock(app):
    for i in range(5):
        with pytest.raises(AccessDenied):
            app.auth.password_step("testadmin", "Incorrect!12345678")
        user = app.store.list("users")[0]
        assert user["next_attempt"] > app.test_clock[0]
        app.test_clock[0] += 31
    assert user["blocked_until"] > app.test_clock[0]
    with pytest.raises(AccessDenied):
        app.auth.password_step("testadmin", app.test_password)
    app.auth.user_action(app.test_admin, user["id"], "unlock")
    assert app.auth.password_step("testadmin", app.test_password)[1] == "challenge"


def test_wrong_totp_rejected_then_valid_and_no_replay(app):
    challenge, _ = app.auth.password_step("testadmin", app.test_password)
    with pytest.raises(AccessDenied):
        app.auth.second_step(challenge, "xxxxxx")
    app.test_clock[0] += 31
    code = pyotp.TOTP(app.test_secret).at(app.test_clock[0])
    token, _ = app.auth.second_step(challenge, code)
    assert app.auth.authorize(token)["role"] == "administrador"
    challenge, _ = app.auth.password_step("testadmin", app.test_password)
    with pytest.raises(AccessDenied):
        app.auth.second_step(challenge, code)


def test_recovery_code_one_use(app):
    challenge, _ = app.auth.password_step("testadmin", app.test_password)
    token, _ = app.auth.second_step(challenge, app.test_codes[0], recovery=True)
    assert app.auth.authorize(token)
    challenge, _ = app.auth.password_step("testadmin", app.test_password)
    with pytest.raises(AccessDenied):
        app.auth.second_step(challenge, app.test_codes[0], recovery=True)
    assert any(r["action"] == "recovery_used" for r in app.store.list("audit_log"))


def test_challenge_is_not_authenticated_and_expires(app):
    challenge, _ = app.auth.password_step("testadmin", app.test_password)
    with pytest.raises(AccessDenied):
        app.auth.authorize(challenge)
    app.test_clock[0] += 301
    with pytest.raises(AccessDenied):
        app.auth.second_step(challenge, app.test_codes[0], recovery=True)


def test_session_expiry_and_logout(app):
    app.test_clock[0] += 901
    with pytest.raises(AccessDenied):
        app.auth.authorize(app.test_admin)


def test_logout_revokes_token_and_audits(app):
    app.auth.logout(app.test_admin)
    with pytest.raises(AccessDenied):
        app.auth.authorize(app.test_admin)
    assert app.store.list("audit_log")[-1]["action"] == "logout"


@pytest.mark.parametrize("permission", ["users", "audit", "backup", "integrity", "settings"])
def test_engineer_cannot_access_administrative_services(app, permission):
    _, token, _ = engineer(app)
    with pytest.raises(AccessDenied):
        app.auth.authorize(token, permission)


def test_admin_permissions_and_last_admin_preserved(app):
    user = app.store.list("users")[0]
    for permission in ("users", "audit", "backup", "integrity", "settings"):
        assert app.auth.authorize(app.test_admin, permission)
    with pytest.raises(ValidationError):
        app.auth.user_action(app.test_admin, user["id"], "active", False)
    with pytest.raises(ValidationError):
        app.auth.user_action(app.test_admin, user["id"], "role", "ingeniero")


@pytest.mark.parametrize(
    "action,value",
    [("active", False), ("reset_totp", None), ("revoke_sessions", None), ("role", "administrador")],
)
def test_user_actions_invalidate_all_sessions(app, action, value):
    user_id, token, _ = engineer(app)
    app.auth.user_action(app.test_admin, user_id, action, value)
    with pytest.raises(AccessDenied):
        app.auth.authorize(token)


def test_change_password_history_and_session_invalidation(app):
    app.auth.change_password(app.test_admin, app.test_password, "NewAster!9382105764")
    with pytest.raises(AccessDenied):
        app.auth.authorize(app.test_admin)
    app.test_clock[0] += 31
    challenge, _ = app.auth.password_step("testadmin", "NewAster!9382105764")
    token, _ = app.auth.second_step(challenge, pyotp.TOTP(app.test_secret).at(app.test_clock[0]))
    with pytest.raises(ValidationError):
        app.auth.change_password(token, "NewAster!9382105764", app.test_password)


def test_regeneration_needs_two_factors_and_invalidates_previous_codes(app):
    app.test_clock[0] += 31
    with pytest.raises(AccessDenied):
        app.auth.regenerate_recovery(app.test_admin, "incorrect", "000000")
    codes = app.auth.regenerate_recovery(
        app.test_admin, app.test_password, pyotp.TOTP(app.test_secret).at(app.test_clock[0])
    )
    stored = {r["hash"] for r in app.store.list("recovery_codes")}
    assert len(codes) == 10 and digest(app.test_codes[0]) not in stored


def test_audit_immutable_and_no_secrets_in_events(app):
    with pytest.raises(Exception):
        with app.store.tx() as c:
            c.execute(db.audit_log.delete())
    with pytest.raises(Exception):
        with app.store.tx() as c:
            c.execute(db.audit_log.update().values(action="changed"))
    assert app.test_secret not in json.dumps(app.store.list("audit_log"))


def test_bootstrap_cannot_create_second_admin_without_authorization(app):
    with pytest.raises(AccessDenied):
        app.auth.bootstrap("another", "Another", "Another!3928105764")


def test_disabled_account_cannot_pass_first_factor(app):
    user_id, _, _ = engineer(app)
    app.auth.user_action(app.test_admin, user_id, "active", False)
    with pytest.raises(AccessDenied):
        app.auth.password_step("testengineer", app.test_permanent)
