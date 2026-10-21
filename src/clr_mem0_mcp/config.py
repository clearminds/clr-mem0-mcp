"""Configuration for the mem0 MCP Server.

Standard credential loading pattern for clearminds MCP servers:
environment variables (MEM0_URL, MEM0_API_KEY, MEM0_USER_ID) as the base,
~/.config/mem0/credentials.json on top for local development.
"""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

CREDS_PATH = Path.home() / ".config" / "mem0" / "credentials.json"


class Settings(BaseSettings):
    """Settings from environment variables and/or credentials.json.

    Attributes:
        mem0_url: Base URL of the mem0 REST API (e.g. https://mem0-api.example.com).
        mem0_api_key: A mem0 API key (X-API-Key): a per-user key made in the dashboard.
        mem0_user_id: Whose memories the tools use when no user_id is given (e.g. "alice").
        mem0_read_only: Hide the add/update/delete tools.
        mem0_transport: stdio or http.
        mem0_log_level: Logging level.
    """

    mem0_url: str = ""
    mem0_api_key: str = ""
    mem0_user_id: str = ""
    mem0_read_only: bool = False

    @field_validator("mem0_read_only", mode="before")
    @classmethod
    def _empty_str_to_false(cls, v: Any) -> Any:
        if v == "":
            return False
        return v

    mem0_transport: str = "stdio"
    mem0_log_level: str = "INFO"

    model_config = {"env_prefix": ""}

    def load_credentials(self) -> dict[str, Any]:
        """Env vars first (base), then ~/.config/mem0/credentials.json overrides.

        Returns:
            Dict with "url", "api_key" and "user_id" where known.
        """
        creds: dict[str, Any] = {}
        if self.mem0_url:
            creds["url"] = self.mem0_url
        if self.mem0_api_key:
            creds["api_key"] = self.mem0_api_key
        if self.mem0_user_id:
            creds["user_id"] = self.mem0_user_id
        if creds:
            logger.info("Using credentials from environment variables")

        if CREDS_PATH.exists():
            try:
                file_creds = json.loads(CREDS_PATH.read_text())
                creds.update({k: v for k, v in file_creds.items() if v})
                logger.info("Loaded credentials from %s", CREDS_PATH)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read %s: %s", CREDS_PATH, exc)

        return creds
