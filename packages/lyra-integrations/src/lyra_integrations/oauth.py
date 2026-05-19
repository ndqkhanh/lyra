"""
OAuth 2.0 Client - Generic OAuth implementation.

Features:
- Authorization code flow
- Token refresh automation
- Secure credential storage
- Multi-account support
"""

import asyncio
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse

import httpx
from cryptography.fernet import Fernet


class GrantType(Enum):
    """OAuth grant types."""

    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"


@dataclass
class OAuthConfig:
    """OAuth provider configuration."""

    provider_name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    scopes: list[str] = field(default_factory=list)
    redirect_uri: str = "http://localhost:8080/callback"


@dataclass
class OAuthToken:
    """OAuth access token."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_in:
            return False
        expiry = self.created_at + timedelta(seconds=self.expires_in)
        # Add 5 minute buffer
        return datetime.now() >= (expiry - timedelta(minutes=5))


class OAuthClient:
    """
    Generic OAuth 2.0 client.

    Supports:
    - Authorization code flow
    - Automatic token refresh
    - Secure token storage
    """

    def __init__(self, config: OAuthConfig, encryption_key: Optional[bytes] = None):
        """
        Initialize OAuth client.

        Args:
            config: OAuth provider configuration
            encryption_key: Fernet encryption key (generated if not provided)
        """
        self.config = config
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.token: Optional[OAuthToken] = None
        self._http_client = httpx.AsyncClient()

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate authorization URL.

        Args:
            state: CSRF protection state (generated if not provided)

        Returns:
            Authorization URL
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }

        return f"{self.config.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthToken:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code

        Returns:
            OAuth token
        """
        data = {
            "grant_type": GrantType.AUTHORIZATION_CODE.value,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        response = await self._http_client.post(
            self.config.token_url,
            data=data,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()

        token_data = response.json()
        self.token = OAuthToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
        )

        return self.token

    async def refresh_access_token(self) -> OAuthToken:
        """
        Refresh access token using refresh token.

        Returns:
            New OAuth token

        Raises:
            ValueError: If no refresh token available
        """
        if not self.token or not self.token.refresh_token:
            raise ValueError("No refresh token available")

        data = {
            "grant_type": GrantType.REFRESH_TOKEN.value,
            "refresh_token": self.token.refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        response = await self._http_client.post(
            self.config.token_url,
            data=data,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()

        token_data = response.json()
        self.token = OAuthToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token", self.token.refresh_token),
            scope=token_data.get("scope"),
        )

        return self.token

    async def get_valid_token(self) -> str:
        """
        Get valid access token, refreshing if necessary.

        Returns:
            Valid access token

        Raises:
            ValueError: If no token available
        """
        if not self.token:
            raise ValueError("No token available. Complete OAuth flow first.")

        if self.token.is_expired:
            await self.refresh_access_token()

        return self.token.access_token

    def encrypt_token(self, token: OAuthToken) -> bytes:
        """
        Encrypt token for secure storage.

        Args:
            token: Token to encrypt

        Returns:
            Encrypted token bytes
        """
        import json

        token_dict = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "refresh_token": token.refresh_token,
            "scope": token.scope,
            "created_at": token.created_at.isoformat(),
        }
        token_json = json.dumps(token_dict)
        return self.cipher.encrypt(token_json.encode())

    def decrypt_token(self, encrypted: bytes) -> OAuthToken:
        """
        Decrypt token from storage.

        Args:
            encrypted: Encrypted token bytes

        Returns:
            Decrypted OAuth token
        """
        import json

        token_json = self.cipher.decrypt(encrypted).decode()
        token_dict = json.loads(token_json)

        return OAuthToken(
            access_token=token_dict["access_token"],
            token_type=token_dict["token_type"],
            expires_in=token_dict["expires_in"],
            refresh_token=token_dict.get("refresh_token"),
            scope=token_dict.get("scope"),
            created_at=datetime.fromisoformat(token_dict["created_at"]),
        )

    async def make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make authenticated API request.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            HTTP response
        """
        token = await self.get_valid_token()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"{self.token.token_type} {token}"

        response = await self._http_client.request(
            method=method,
            url=url,
            headers=headers,
            **kwargs,
        )

        return response

    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
