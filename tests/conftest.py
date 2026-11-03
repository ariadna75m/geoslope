import secrets
import sys
import time
from pathlib import Path
import pyotp
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gsreview.application.container import Container


@pytest.fixture
def app(tmp_path):
    clock = [time.time() + 60]
    c = Container(runtime=tmp_path, clock=lambda: clock[0])
    c.test_clock = clock
    c.test_password = "Gs!" + secrets.token_hex(12)
    c.test_temporary = "Tmp!" + secrets.token_hex(12)
    c.test_permanent = "Next!" + secrets.token_hex(12)
    challenge = c.auth.bootstrap("testadmin", "Administrador sintético", c.test_password)
    _, secret = c.auth.enrollment(challenge)
    token, codes = c.auth.second_step(challenge, pyotp.TOTP(secret).at(clock[0]), enroll=True)
    c.test_admin, c.test_secret, c.test_codes = token, secret, codes
    return c


def engineer(c):
    user_id = c.auth.create_user(
        c.test_admin, "testengineer", "Ingeniero sintético", c.test_temporary, "ingeniero"
    )
    challenge, stage = c.auth.password_step("testengineer", c.test_temporary)
    _, secret = c.auth.enrollment(challenge)
    token, _ = c.auth.second_step(challenge, pyotp.TOTP(secret).at(c.test_clock[0]), enroll=True)
    c.auth.change_password(token, c.test_temporary, c.test_permanent)
    c.test_clock[0] += 31
    challenge, _ = c.auth.password_step("testengineer", c.test_permanent)
    token, _ = c.auth.second_step(challenge, pyotp.TOTP(secret).at(c.test_clock[0]))
    return user_id, token, secret
