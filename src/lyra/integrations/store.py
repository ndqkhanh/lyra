"""
Credential Store - Secure storage for OAuth tokens.

Features:
- SQLite-based encrypted storage
- Multi-account support per provider
- Automatic token refresh
- Secure key management
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiosqlite
from cryptography.fernet import Fernet

from lyra.integrations.oauth import OAuthToken


@dataclass
class StoredCredential:
    """Stored credential metadata."""

    provider: str
    account_id: str
    account_name: str
    encrypted_token: bytes
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, str]


class CredentialStore:
    """
    Secure credential storage.

    Architecture:
    - SQLite database for metadata
    - Fernet encryption for tokens
    - Per-provider multi-account support
    """

    def __init__(self, db_path: Path, encryption_key: bytes | None = None):
        """
        Initialize credential store.

        Args:
            db_path: Path to SQLite database
            encryption_key: Fernet encryption key (generated if not provided)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)

        self._db: aiosqlite.Connection | None = None

    async def initialize(self):
        """Initialize database schema."""
        self._db = await aiosqlite.connect(str(self.db_path))

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                account_id TEXT NOT NULL,
                account_name TEXT NOT NULL,
                encrypted_token BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT,
                UNIQUE(provider, account_id)
            )
            """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider
            ON credentials(provider)
            """)

        await self._db.commit()

    async def store_credential(
        self,
        provider: str,
        account_id: str,
        account_name: str,
        token: OAuthToken,
        metadata: dict[str, str] | None = None,
    ):
        """
        Store OAuth credential.

        Args:
            provider: Provider name (e.g., "github", "shodan")
            account_id: Unique account identifier
            account_name: Human-readable account name
            token: OAuth token
            metadata: Additional metadata
        """
        # Encrypt token
        token_dict = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "refresh_token": token.refresh_token,
            "scope": token.scope,
            "created_at": token.created_at.isoformat(),
        }
        token_json = json.dumps(token_dict)
        encrypted_token = self.cipher.encrypt(token_json.encode())

        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})

        await self._db.execute(
            """
            INSERT OR REPLACE INTO credentials
            (provider, account_id, account_name, encrypted_token, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM credentials WHERE provider=? AND
            account_id=?), ?), ?, ?)
            """,
            (
                provider,
                account_id,
                account_name,
                encrypted_token,
                provider,
                account_id,
                now,
                now,
                metadata_json,
            ),
        )

        await self._db.commit()

    async def get_credential(
        self,
        provider: str,
        account_id: str,
    ) -> OAuthToken | None:
        """
        Retrieve OAuth credential.

        Args:
            provider: Provider name
            account_id: Account identifier

        Returns:
            OAuth token if found, None otherwise
        """
        cursor = await self._db.execute(
            """
            SELECT encrypted_token FROM credentials
            WHERE provider = ? AND account_id = ?
            """,
            (provider, account_id),
        )

        row = await cursor.fetchone()
        if not row:
            return None

        # Decrypt token
        encrypted_token = row[0]
        token_json = self.cipher.decrypt(encrypted_token).decode()
        token_dict = json.loads(token_json)

        return OAuthToken(
            access_token=token_dict["access_token"],
            token_type=token_dict["token_type"],
            expires_in=token_dict["expires_in"],
            refresh_token=token_dict.get("refresh_token"),
            scope=token_dict.get("scope"),
            created_at=datetime.fromisoformat(token_dict["created_at"]),
        )

    async def list_credentials(self, provider: str | None = None) -> list[StoredCredential]:
        """
        List stored credentials.

        Args:
            provider: Filter by provider (None for all)

        Returns:
            List of stored credentials
        """
        if provider:
            cursor = await self._db.execute(
                """
                SELECT provider, account_id, account_name, encrypted_token,
                       created_at, updated_at, metadata
                FROM credentials
                WHERE provider = ?
                ORDER BY updated_at DESC
                """,
                (provider,),
            )
        else:
            cursor = await self._db.execute("""
                SELECT provider, account_id, account_name, encrypted_token,
                       created_at, updated_at, metadata
                FROM credentials
                ORDER BY provider, updated_at DESC
                """)

        rows = await cursor.fetchall()
        credentials = []

        for row in rows:
            metadata = json.loads(row[6]) if row[6] else {}
            credentials.append(
                StoredCredential(
                    provider=row[0],
                    account_id=row[1],
                    account_name=row[2],
                    encrypted_token=row[3],
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5]),
                    metadata=metadata,
                )
            )

        return credentials

    async def delete_credential(self, provider: str, account_id: str):
        """
        Delete credential.

        Args:
            provider: Provider name
            account_id: Account identifier
        """
        await self._db.execute(
            """
            DELETE FROM credentials
            WHERE provider = ? AND account_id = ?
            """,
            (provider, account_id),
        )

        await self._db.commit()

    async def update_token(
        self,
        provider: str,
        account_id: str,
        token: OAuthToken,
    ):
        """
        Update stored token (e.g., after refresh).

        Args:
            provider: Provider name
            account_id: Account identifier
            token: New OAuth token
        """
        # Encrypt token
        token_dict = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "refresh_token": token.refresh_token,
            "scope": token.scope,
            "created_at": token.created_at.isoformat(),
        }
        token_json = json.dumps(token_dict)
        encrypted_token = self.cipher.encrypt(token_json.encode())

        now = datetime.now().isoformat()

        await self._db.execute(
            """
            UPDATE credentials
            SET encrypted_token = ?, updated_at = ?
            WHERE provider = ? AND account_id = ?
            """,
            (encrypted_token, now, provider, account_id),
        )

        await self._db.commit()

    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
