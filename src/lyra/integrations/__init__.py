"""
Lyra Integrations - OAuth integration system for cyber security.

This package provides:
- Generic OAuth 2.0 client
- Secure credential storage
- 50+ cyber-focused integrations
- Auto-fetch engine (20-minute sync)
- Integration registry
"""

from lyra.integrations.auto_fetch import AutoFetchEngine, SyncJob, SyncResult, SyncStatus
from lyra.integrations.oauth import GrantType, OAuthClient, OAuthConfig, OAuthToken
from lyra.integrations.providers import (
    GitHubIntegration,
    IntegrationProvider,
    ShodanIntegration,
    get_provider,
    list_providers,
)
from lyra.integrations.store import CredentialStore, StoredCredential

__version__ = "0.1.0"

__all__ = [
    # OAuth
    "OAuthClient",
    "OAuthConfig",
    "OAuthToken",
    "GrantType",
    # Store
    "CredentialStore",
    "StoredCredential",
    # Providers
    "IntegrationProvider",
    "GitHubIntegration",
    "ShodanIntegration",
    "get_provider",
    "list_providers",
    # Auto-fetch
    "AutoFetchEngine",
    "SyncJob",
    "SyncResult",
    "SyncStatus",
]
