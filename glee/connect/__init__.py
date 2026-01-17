"""Connect module for Glee connections."""

from glee.connect.connection import ChatResponse, Connection
from glee.connect.credential import (
    AIProviderAPICredential,
    AIProviderCredential,
    AIProviderOAuthCredential,
    APICredential,
    Category,
    Credential,
    OAuthCredential,
    SDK,
    ServiceCredential,
)
from glee.connect.storage import (
    VENDOR_URLS,
    ConnectionStorage,
)

__all__ = [
    # New types
    "AIProviderAPICredential",
    "AIProviderCredential",
    "AIProviderOAuthCredential",
    "ServiceCredential",
    # Legacy aliases
    "APICredential",
    "OAuthCredential",
    # Other exports
    "Category",
    "ChatResponse",
    "Connection",
    "ConnectionStorage",
    "Credential",
    "SDK",
    "VENDOR_URLS",
]
