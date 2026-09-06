"""Regression tests for `core/db` (NUMA-142 P6).

DSN parsing. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


@pytest.mark.parametrize(
    "url, expected_user, expected_password, expected_dbname",
    [
        # The query string Supabase hands out was read as part of the db name.
        (
            "postgresql://postgres:secret@db.example.co:5432/postgres?sslmode=require",
            "postgres", "secret", "postgres",
        ),
        # A percent-encoded password was sent literally.
        (
            "postgresql://postgres:p%40ss@db.example.co:5432/postgres",
            "postgres", "p@ss", "postgres",
        ),
        # `#`, `?` and `/` in a password each ended the authority early and
        # failed the boot once the parser moved to urlsplit.
        (
            "postgresql://postgres:Str0ng#Pass@db.example.co:5432/postgres",
            "postgres", "Str0ng#Pass", "postgres",
        ),
        (
            "postgresql://postgres:a?b@db.example.co:5432/postgres",
            "postgres", "a?b", "postgres",
        ),
        (
            "postgresql://postgres:pa/ss@db.example.co:5432/postgres",
            "postgres", "pa/ss", "postgres",
        ),
        # An `@` inside the password still splits on the last one.
        (
            "postgresql://postgres:a@b@db.example.co:5432/postgres",
            "postgres", "a@b", "postgres",
        ),
        # No password at all: `find(":")` returned -1 and the slices produced a
        # silently wrong user and password rather than an error.
        (
            "postgresql://someuser@db.example.co:5432/postgres",
            "someuser", "", "postgres",
        ),
    ],
)
def test_parse_database_url_shapes(monkeypatch, url, expected_user, expected_password, expected_dbname):
    from src.core.db import _parse_database_url

    monkeypatch.setenv("DATABASE_URL", url)
    params = _parse_database_url()

    assert params["user"] == expected_user
    assert params["password"] == expected_password
    assert params["dbname"] == expected_dbname
    assert params["host"] == "db.example.co"
    assert params["port"] == 5432
    # Pinned as policy: a URL asking to turn TLS off is not honoured.
    assert params["sslmode"] == "require"


def test_parse_database_url_rejects_a_bad_scheme(monkeypatch):
    from src.core.db import _parse_database_url

    monkeypatch.setenv("DATABASE_URL", "mysql://u:p@host:3306/db")
    with pytest.raises(ValueError):
        _parse_database_url()
