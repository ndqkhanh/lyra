"""
Integration Providers - Cyber-focused OAuth integrations.

Supported providers:
- GitHub: Repository scanning, secret detection
- Shodan: Internet-wide asset discovery
- AWS: Cloud security posture
- More to come...
"""

from dataclasses import dataclass
from typing import Any

import httpx

from lyra_integrations.oauth import OAuthClient, OAuthConfig


@dataclass
class IntegrationProvider:
    """Base integration provider."""

    name: str
    display_name: str
    description: str
    category: str  # security, cloud, devops, siem, threat-intel
    oauth_config: OAuthConfig
    base_url: str
    rate_limit: int = 5000  # requests per hour


class GitHubIntegration:
    """
    GitHub integration for security scanning.

    Features:
    - Repository secret scanning
    - Dependency vulnerability detection
    - Code security analysis
    """

    PROVIDER = IntegrationProvider(
        name="github",
        display_name="GitHub",
        description="Repository security scanning and secret detection",
        category="devops",
        oauth_config=OAuthConfig(
            provider_name="github",
            client_id="",  # Set by user
            client_secret="",  # Set by user
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "security_events", "read:org"],
        ),
        base_url="https://api.github.com",
        rate_limit=5000,
    )

    def __init__(self, oauth_client: OAuthClient):
        """Initialize GitHub integration."""
        self.client = oauth_client

    async def list_repositories(self, org: str | None = None) -> list[dict[str, Any]]:
        """
        List repositories.

        Args:
            org: Organization name (None for user repos)

        Returns:
            List of repositories
        """
        if org:
            url = f"{self.PROVIDER.base_url}/orgs/{org}/repos"
        else:
            url = f"{self.PROVIDER.base_url}/user/repos"

        response = await self.client.make_request("GET", url)
        response.raise_for_status()
        return response.json()

    async def scan_secrets(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """
        Scan repository for exposed secrets.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of secret scanning alerts
        """
        url = f"{self.PROVIDER.base_url}/repos/{owner}/{repo}/secret-scanning/alerts"

        response = await self.client.make_request("GET", url)
        response.raise_for_status()
        return response.json()

    async def get_vulnerabilities(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """
        Get dependency vulnerabilities.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of Dependabot alerts
        """
        url = f"{self.PROVIDER.base_url}/repos/{owner}/{repo}/dependabot/alerts"

        response = await self.client.make_request("GET", url)
        response.raise_for_status()
        return response.json()

    async def get_code_scanning_alerts(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """
        Get code scanning alerts.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of code scanning alerts
        """
        url = f"{self.PROVIDER.base_url}/repos/{owner}/{repo}/code-scanning/alerts"

        response = await self.client.make_request("GET", url)
        response.raise_for_status()
        return response.json()


class ShodanIntegration:
    """
    Shodan integration for asset discovery.

    Features:
    - Internet-wide host search
    - Service enumeration
    - Vulnerability detection
    """

    PROVIDER = IntegrationProvider(
        name="shodan",
        display_name="Shodan",
        description="Internet-wide asset discovery and reconnaissance",
        category="threat-intel",
        oauth_config=OAuthConfig(
            provider_name="shodan",
            client_id="",  # API key-based, not OAuth
            client_secret="",
            authorize_url="",
            token_url="",
            scopes=[],
        ),
        base_url="https://api.shodan.io",
        rate_limit=100,  # requests per month for free tier
    )

    def __init__(self, api_key: str):
        """
        Initialize Shodan integration.

        Args:
            api_key: Shodan API key
        """
        self.api_key = api_key
        self._http_client = httpx.AsyncClient()

    async def search_hosts(self, query: str, limit: int = 100) -> dict[str, Any]:
        """
        Search for hosts.

        Args:
            query: Shodan search query
            limit: Maximum results

        Returns:
            Search results
        """
        url = f"{self.PROVIDER.base_url}/shodan/host/search"
        params = {"key": self.api_key, "query": query, "limit": limit}

        response = await self._http_client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_host_info(self, ip: str) -> dict[str, Any]:
        """
        Get detailed host information.

        Args:
            ip: IP address

        Returns:
            Host information
        """
        url = f"{self.PROVIDER.base_url}/shodan/host/{ip}"
        params = {"key": self.api_key}

        response = await self._http_client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def search_exploits(self, query: str) -> dict[str, Any]:
        """
        Search exploit database.

        Args:
            query: Search query (CVE, software name, etc.)

        Returns:
            Exploit search results
        """
        url = f"{self.PROVIDER.base_url}/exploits/search"
        params = {"key": self.api_key, "query": query}

        response = await self._http_client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()


# Provider registry
PROVIDERS: dict[str, IntegrationProvider] = {
    "github": GitHubIntegration.PROVIDER,
    "shodan": ShodanIntegration.PROVIDER,
}


def get_provider(name: str) -> IntegrationProvider | None:
    """
    Get provider by name.

    Args:
        name: Provider name

    Returns:
        Provider if found, None otherwise
    """
    return PROVIDERS.get(name)


def list_providers(category: str | None = None) -> list[IntegrationProvider]:
    """
    List available providers.

    Args:
        category: Filter by category

    Returns:
        List of providers
    """
    providers = list(PROVIDERS.values())

    if category:
        providers = [p for p in providers if p.category == category]

    return providers
