"""Tests for OAuth client."""

from datetime import datetime, timedelta

import pytest

from lyra_integrations.oauth import OAuthClient, OAuthConfig, OAuthToken


def test_oauth_config_creation():
    """Test creating OAuth configuration."""
    config = OAuthConfig(
        provider_name="github",
        client_id="test_client_id",
        client_secret="test_secret",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scopes=["repo", "user"],
    )

    assert config.provider_name == "github"
    assert config.client_id == "test_client_id"
    assert len(config.scopes) == 2


def test_oauth_token_expiry():
    """Test token expiry detection."""
    # Fresh token
    token = OAuthToken(
        access_token="test_token",
        expires_in=3600,
        created_at=datetime.now(),
    )
    assert not token.is_expired

    # Expired token
    old_token = OAuthToken(
        access_token="test_token",
        expires_in=3600,
        created_at=datetime.now() - timedelta(hours=2),
    )
    assert old_token.is_expired


def test_authorization_url_generation():
    """Test generating authorization URL."""
    config = OAuthConfig(
        provider_name="github",
        client_id="test_client",
        client_secret="test_secret",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scopes=["repo"],
    )

    client = OAuthClient(config)
    auth_url = client.get_authorization_url(state="test_state")

    assert "https://github.com/login/oauth/authorize" in auth_url
    assert "client_id=test_client" in auth_url
    assert "state=test_state" in auth_url
    assert "scope=repo" in auth_url


def test_token_encryption():
    """Test token encryption/decryption."""
    config = OAuthConfig(
        provider_name="test",
        client_id="test",
        client_secret="test",
        authorize_url="https://test.com/auth",
        token_url="https://test.com/token",
    )

    client = OAuthClient(config)

    token = OAuthToken(
        access_token="secret_token",
        refresh_token="secret_refresh",
        expires_in=3600,
    )

    # Encrypt
    encrypted = client.encrypt_token(token)
    assert isinstance(encrypted, bytes)
    assert b"secret_token" not in encrypted  # Should be encrypted

    # Decrypt
    decrypted = client.decrypt_token(encrypted)
    assert decrypted.access_token == "secret_token"
    assert decrypted.refresh_token == "secret_refresh"


@pytest.mark.asyncio
async def test_get_valid_token_no_token():
    """Test getting valid token when none exists."""
    config = OAuthConfig(
        provider_name="test",
        client_id="test",
        client_secret="test",
        authorize_url="https://test.com/auth",
        token_url="https://test.com/token",
    )

    client = OAuthClient(config)

    with pytest.raises(ValueError, match="No token available"):
        await client.get_valid_token()

    await client.close()
