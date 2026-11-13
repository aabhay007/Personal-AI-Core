"""Factory for creating database connectors from configurations or models."""
from typing import Any, Dict, Optional
from app.models.integration import Integration
from app.integrations.base import BaseDatabaseConnector
from app.integrations.postgres import PostgresConnector
from app.integrations.sqlite import SqliteConnector
from app.integrations.encryption import decrypt_secret


def create_connector_from_model(integration: Integration) -> BaseDatabaseConnector:
    """Instantiate a BaseDatabaseConnector from an Integration SQLAlchemy model instance."""
    raw_password = decrypt_secret(integration.encrypted_password)

    if integration.integration_type == "sqlite":
        # database field stores the sqlite file path
        path = integration.database or ":memory:"
        return SqliteConnector(database_path=path)

    elif integration.integration_type in ("postgres", "postgresql"):
        return PostgresConnector(
            host=integration.host or "localhost",
            port=integration.port or 5432,
            database=integration.database or "postgres",
            username=integration.username,
            password=raw_password,
            ssl_mode=integration.ssl_mode or "prefer"
        )
    else:
        raise ValueError(f"Unsupported database integration type: '{integration.integration_type}'")


def create_connector_from_params(
    integration_type: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    ssl_mode: str = "prefer",
    options: Optional[Dict[str, Any]] = None
) -> BaseDatabaseConnector:
    """Instantiate a BaseDatabaseConnector from raw dictionary params (e.g. for testing unsaved connection)."""
    if integration_type == "sqlite":
        path = database or (options.get("path") if options else None) or ":memory:"
        return SqliteConnector(database_path=path)

    elif integration_type in ("postgres", "postgresql"):
        return PostgresConnector(
            host=host or "localhost",
            port=port or 5432,
            database=database or "postgres",
            username=username,
            password=password,
            ssl_mode=ssl_mode
        )
    else:
        raise ValueError(f"Unsupported database integration type: '{integration_type}'")
