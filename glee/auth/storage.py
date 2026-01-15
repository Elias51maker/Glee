"""Auth storage for Glee credentials.

Stores credentials in separate files under ~/.glee/auth/:

```
~/.glee/auth/
  codex-oauth.yml      # OAuth credentials for Codex
  copilot-oauth.yml    # OAuth credentials for GitHub Copilot
  claude-api-key.yml   # API key for Claude
  gemini-api-key.yml   # API key for Gemini
```

Each file contains the credentials for a single provider:

```yaml
# codex-oauth.yml
access_token: "..."
refresh_token: "..."
expires_at: 1736956800
account_id: "org-xxx"

# claude-api-key.yml
api_key: "sk-ant-..."
```

Resolution order:
1. Environment variable (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
2. Project .glee/auth/{provider}-*.yml
3. Global ~/.glee/auth/{provider}-*.yml
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml


# Environment variable mapping
ENV_VAR_MAP = {
    "codex": "OPENAI_API_KEY",
    "copilot": "GITHUB_TOKEN",
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

# Supported providers
PROVIDERS = ["codex", "copilot", "claude", "gemini"]


@dataclass
class OAuthCredentials:
    """OAuth credentials."""

    method: Literal["oauth"] = "oauth"
    access_token: str = ""
    refresh_token: str = ""
    expires_at: int = 0  # Unix timestamp
    account_id: str | None = None

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires_at == 0:
            return False  # No expiry (e.g., Copilot)
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML storage."""
        d = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }
        if self.account_id:
            d["account_id"] = self.account_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> OAuthCredentials:
        """Create from dictionary."""
        return cls(
            method="oauth",
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            expires_at=data.get("expires_at", 0),
            account_id=data.get("account_id"),
        )


@dataclass
class APIKeyCredentials:
    """API key credentials."""

    method: Literal["api_key"] = "api_key"
    api_key: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML storage."""
        return {
            "api_key": self.api_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> APIKeyCredentials:
        """Create from dictionary."""
        return cls(
            method="api_key",
            api_key=data.get("api_key", ""),
        )


# Union type for credentials
Credentials = OAuthCredentials | APIKeyCredentials


class AuthStorage:
    """Manage auth storage in YAML files.

    Each provider has its own file under the auth directory:
    - {auth_dir}/codex-oauth.yml
    - {auth_dir}/claude-api-key.yml
    """

    def __init__(self, auth_dir: Path | str):
        """Initialize with path to auth directory."""
        self.auth_dir = Path(auth_dir).expanduser()

    def _ensure_dir(self) -> None:
        """Ensure the auth directory exists with secure permissions."""
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        # Set directory permissions to 700 (owner only)
        os.chmod(self.auth_dir, 0o700)

    def _get_file_path(self, provider: str, method: str) -> Path:
        """Get the file path for a provider's credentials."""
        return self.auth_dir / f"{provider}-{method}.yml"

    def _read_file(self, path: Path) -> dict:
        """Read a credential file."""
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _write_file(self, path: Path, data: dict) -> None:
        """Write to a credential file with secure permissions."""
        self._ensure_dir()
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        # Set file permissions to 600 (owner read/write only)
        os.chmod(path, 0o600)

    def get(self, provider: str) -> Credentials | None:
        """Get credentials for a provider."""
        # Try OAuth first
        oauth_path = self._get_file_path(provider, "oauth")
        if oauth_path.exists():
            data = self._read_file(oauth_path)
            if data:
                return OAuthCredentials.from_dict(data)

        # Then try API key
        api_key_path = self._get_file_path(provider, "api-key")
        if api_key_path.exists():
            data = self._read_file(api_key_path)
            if data:
                return APIKeyCredentials.from_dict(data)

        return None

    def save(self, provider: str, credentials: Credentials) -> None:
        """Save credentials for a provider."""
        if isinstance(credentials, OAuthCredentials):
            method = "oauth"
        else:
            method = "api-key"

        path = self._get_file_path(provider, method)
        self._write_file(path, credentials.to_dict())

    def delete(self, provider: str) -> bool:
        """Delete credentials for a provider. Returns True if deleted."""
        deleted = False

        # Delete OAuth file if exists
        oauth_path = self._get_file_path(provider, "oauth")
        if oauth_path.exists():
            oauth_path.unlink()
            deleted = True

        # Delete API key file if exists
        api_key_path = self._get_file_path(provider, "api-key")
        if api_key_path.exists():
            api_key_path.unlink()
            deleted = True

        return deleted

    def list_providers(self) -> list[str]:
        """List all providers with saved credentials."""
        providers = set()
        if not self.auth_dir.exists():
            return []

        for path in self.auth_dir.glob("*-oauth.yml"):
            provider = path.stem.rsplit("-oauth", 1)[0]
            providers.add(provider)

        for path in self.auth_dir.glob("*-api-key.yml"):
            provider = path.stem.rsplit("-api-key", 1)[0]
            providers.add(provider)

        return sorted(providers)


def _get_global_storage() -> AuthStorage:
    """Get the global auth storage (~/.glee/auth/)."""
    return AuthStorage(Path.home() / ".glee" / "auth")


def _get_project_storage() -> AuthStorage | None:
    """Get the project auth storage (.glee/auth/) if it exists."""
    project_path = Path.cwd() / ".glee" / "auth"
    if project_path.exists():
        return AuthStorage(project_path)
    return None


def get_credentials(provider: str) -> Credentials | None:
    """Get credentials for a provider with resolution order.

    Resolution order:
    1. Environment variable
    2. Project .glee/auth.yml
    3. Global ~/.glee/auth.yml
    """
    # 1. Check environment variable
    env_var = ENV_VAR_MAP.get(provider)
    if env_var:
        value = os.environ.get(env_var)
        if value:
            return APIKeyCredentials(api_key=value)

    # 2. Check project storage
    project_storage = _get_project_storage()
    if project_storage:
        creds = project_storage.get(provider)
        if creds:
            return creds

    # 3. Check global storage
    global_storage = _get_global_storage()
    return global_storage.get(provider)


def save_credentials(
    provider: str, credentials: Credentials, *, project: bool = False
) -> None:
    """Save credentials for a provider.

    Args:
        provider: Provider name (codex, copilot, claude, gemini)
        credentials: Credentials to save
        project: If True, save to project .glee/auth/ instead of global
    """
    if project:
        storage = AuthStorage(Path.cwd() / ".glee" / "auth")
    else:
        storage = _get_global_storage()
    storage.save(provider, credentials)


def delete_credentials(provider: str, *, project: bool = False) -> bool:
    """Delete credentials for a provider.

    Args:
        provider: Provider name
        project: If True, delete from project storage

    Returns:
        True if credentials were deleted
    """
    if project:
        storage = AuthStorage(Path.cwd() / ".glee" / "auth")
    else:
        storage = _get_global_storage()
    return storage.delete(provider)


def list_providers() -> dict[str, dict]:
    """List all configured providers with their status.

    Returns:
        Dict mapping provider name to status info
    """
    result = {}

    for provider in PROVIDERS:
        creds = get_credentials(provider)
        if creds is None:
            result[provider] = {"configured": False}
        elif isinstance(creds, OAuthCredentials):
            result[provider] = {
                "configured": True,
                "method": "oauth",
                "expired": creds.is_expired(),
                "account_id": creds.account_id,
            }
        else:
            result[provider] = {
                "configured": True,
                "method": "api_key",
                "masked_key": creds.api_key[:8] + "..." if len(creds.api_key) > 8 else "***",
            }

    return result
