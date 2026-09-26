"""The redactor covers the shapes the audit found passing, in linear time (audit 2026-09-27 B-4, B-6).

docs/research/2026-09-27-the-redactor-knows-the-missing-shapes.md
"""
from __future__ import annotations

import time

import pytest
from secret_redact import redact_secrets

from tests.slow_machine import SHORT_TIMEOUT

SECRETS = [
    ("sshpass -p hunter2pass ssh host", "hunter2pass"),
    ("sshpass -p 'pw with space' ssh host", "with space"),
    ("docker login -p Hunter2secret registry.example", "Hunter2secret"),
    ("mysql -pS3cretpw db", "S3cretpw"),
    ("curl 'https://example.test/api?api_key=AbC123xyz987&x=1'", "AbC123xyz987"),
    ("GET /x?access_token=ya29.a0AfH6SMBxQwErTy12345", "a0AfH6SMBxQwErTy12345"),
    ("Authorization uses ya29.a0AfH6SMBxQwErTy1234567890", "a0AfH6SMBxQwErTy1234567890"),
    ("bot 123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw1 ok", "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw1"),
    ("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "ABC-DEF1234ghIkl-zyx57W2v1u123ew11"),
    ("post to https://hooks.slack.com/services/T0001/B0002/XyZ123abcDEF", "XyZ123abcDEF"),
    ("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAabcdef\n", "MIIEowIBAAKCAQEAabcdef"),
]
KEPT = ["mysql -p db", "sshpass -e ssh host", "docker login -u me --password-stdin", "see ?page=2&sort=asc"]


@pytest.mark.parametrize(("text", "secret"), SECRETS)
def test_each_shape_is_redacted(text: str, secret: str) -> None:
    assert secret not in redact_secrets(text)


@pytest.mark.parametrize("text", KEPT)
def test_what_is_not_a_secret_is_kept(text: str) -> None:
    assert redact_secrets(text) == text


# Every rule meets its own alphabet repeated: a scheme run, a command name, a flag.
ADVERSARIAL = ["a." * 100_000, "mysql " * 35_000, "sshpass " * 25_000, "docker login " * 16_000, "-p " * 70_000]


@pytest.mark.parametrize("text", ADVERSARIAL, ids=lambda text: text[:8].strip())
def test_a_long_crafted_line_is_redacted_in_linear_time(text: str) -> None:
    deadline = time.monotonic() + SHORT_TIMEOUT

    redact_secrets(text)

    assert time.monotonic() < deadline
