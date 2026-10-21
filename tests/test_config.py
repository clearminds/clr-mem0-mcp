"""Tests for configuration loading (env vars as base, credentials.json on top)."""

import json

from clr_mem0_mcp.config import Settings


def test_env_vars_alone(tmp_path, monkeypatch):
    monkeypatch.setattr("clr_mem0_mcp.config.CREDS_PATH", tmp_path / "missing.json")
    monkeypatch.setenv("MEM0_URL", "https://env.example.com")
    monkeypatch.setenv("MEM0_API_KEY", "env-key")
    monkeypatch.setenv("MEM0_USER_ID", "env-user")

    creds = Settings().load_credentials()

    assert creds == {"url": "https://env.example.com", "api_key": "env-key", "user_id": "env-user"}


def test_file_overrides_env(tmp_path, monkeypatch):
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({"url": "https://file.example.com", "api_key": "file-key"}))
    monkeypatch.setattr("clr_mem0_mcp.config.CREDS_PATH", creds_file)
    monkeypatch.setenv("MEM0_URL", "https://env.example.com")
    monkeypatch.setenv("MEM0_API_KEY", "env-key")
    monkeypatch.setenv("MEM0_USER_ID", "alice")

    creds = Settings().load_credentials()

    assert creds["url"] == "https://file.example.com"
    assert creds["api_key"] == "file-key"
    assert creds["user_id"] == "alice"  # not in the file: env value kept


def test_empty_file_values_do_not_override(tmp_path, monkeypatch):
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({"url": "", "api_key": "file-key"}))
    monkeypatch.setattr("clr_mem0_mcp.config.CREDS_PATH", creds_file)
    monkeypatch.setenv("MEM0_URL", "https://env.example.com")
    monkeypatch.delenv("MEM0_API_KEY", raising=False)
    monkeypatch.delenv("MEM0_USER_ID", raising=False)

    creds = Settings().load_credentials()

    assert creds == {"url": "https://env.example.com", "api_key": "file-key"}


def test_nothing_configured(tmp_path, monkeypatch):
    monkeypatch.setattr("clr_mem0_mcp.config.CREDS_PATH", tmp_path / "missing.json")
    for var in ("MEM0_URL", "MEM0_API_KEY", "MEM0_USER_ID"):
        monkeypatch.delenv(var, raising=False)

    assert Settings().load_credentials() == {}


def test_read_only_empty_string_is_false(monkeypatch):
    monkeypatch.setenv("MEM0_READ_ONLY", "")
    assert Settings().mem0_read_only is False
