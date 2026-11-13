"""Base interface and validation for database connectors."""
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Regular expression to strictly validate SQL identifiers (tables, columns, schemas)
# Prevents SQL injection via identifier tampering
IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_identifier(name: str, identifier_type: str = "identifier") -> str:
    """Validate that a SQL identifier contains only alphanumeric characters and underscores."""
    if not name or not IDENTIFIER_REGEX.match(name.strip()):
        raise ValueError(
            f"Invalid SQL {identifier_type} '{name}'. Must start with a letter or underscore and contain only alphanumeric characters."
        )
    return name.strip()


class BaseDatabaseConnector(ABC):
    """Abstract base class defining standardized database operations."""

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity and return status, latency_ms, and database version."""
        pass

    @abstractmethod
    async def get_schemas(self) -> List[str]:
        """List accessible schemas in the database."""
        pass

    @abstractmethod
    async def get_tables(self, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve table schemas including column names, types, nullability, and keys."""
        pass

    @abstractmethod
    async def execute_read_query(
        self,
        table: str,
        schema_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Safely execute a parameterized read-only SELECT query with strict row limit and column filtering."""
        pass
