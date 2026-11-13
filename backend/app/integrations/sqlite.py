"""SQLite Database Connector using aiosqlite."""
import time
import logging
from typing import Any, Dict, List, Optional
import aiosqlite
from app.integrations.base import BaseDatabaseConnector, validate_identifier

logger = logging.getLogger(__name__)


class SqliteConnector(BaseDatabaseConnector):
    """SQLite connector supporting introspection and safe parameterized queries."""

    def __init__(self, database_path: str, timeout: int = 5):
        self.database_path = database_path
        self.timeout = timeout

    async def test_connection(self) -> Dict[str, Any]:
        """Test opening the SQLite database and retrieving version."""
        start_time = time.perf_counter()
        try:
            async with aiosqlite.connect(self.database_path, timeout=self.timeout) as db:
                async with db.execute("SELECT sqlite_version();") as cursor:
                    row = await cursor.fetchone()
                    version = row[0] if row else "unknown"
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": True,
                "latency_ms": latency_ms,
                "version": f"SQLite {version}",
                "database": self.database_path,
                "error": None
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"SQLite connection test failed: {e}")
            return {
                "success": False,
                "latency_ms": latency_ms,
                "version": None,
                "database": self.database_path,
                "error": str(e)
            }

    async def get_schemas(self) -> List[str]:
        """SQLite only has a single main schema."""
        return ["main"]

    async def get_tables(self, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Introspect all user tables and columns using sqlite_master and PRAGMA table_info."""
        tables = []
        async with aiosqlite.connect(self.database_path, timeout=self.timeout) as db:
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            ) as cursor:
                table_rows = await cursor.fetchall()

            for t_row in table_rows:
                t_name = t_row[0]
                cols = []
                async with db.execute(f"PRAGMA table_info('{t_name}');") as col_cursor:
                    # pragma returns: (cid, name, type, notnull, dflt_value, pk)
                    for col in await col_cursor.fetchall():
                        cols.append({
                            "name": col[1],
                            "data_type": col[2],
                            "is_nullable": not bool(col[3]),
                            "default": col[4],
                            "is_primary_key": bool(col[5])
                        })
                tables.append({
                    "table_name": t_name,
                    "schema": "main",
                    "columns": cols
                })
        return tables

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
        """Safely execute a read-only parameterized query against SQLite."""
        safe_table = validate_identifier(table, "table name")

        if columns and len(columns) > 0:
            safe_cols = [validate_identifier(c, "column name") for c in columns]
            cols_clause = ", ".join(f'"{c}"' for c in safe_cols)
        else:
            cols_clause = "*"

        where_clauses = []
        params = []
        if filters:
            for col_name, val in filters.items():
                safe_col = validate_identifier(col_name, "filter column")
                where_clauses.append(f'"{safe_col}" = ?')
                params.append(val)

        where_stmt = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        order_stmt = ""
        if order_by:
            safe_order = validate_identifier(order_by, "order_by column")
            direction = "DESC" if order_desc else "ASC"
            order_stmt = f'ORDER BY "{safe_order}" {direction}'

        safe_limit = min(max(1, limit), 100)
        safe_offset = max(0, offset)

        query = f'SELECT {cols_clause} FROM "{safe_table}" {where_stmt} {order_stmt} LIMIT ? OFFSET ?;'
        params.extend([safe_limit, safe_offset])

        start_time = time.perf_counter()
        async with aiosqlite.connect(self.database_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                records = await cursor.fetchall()
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                rows = []
                col_names = []
                if records:
                    col_names = list(records[0].keys())
                    for r in records:
                        rows.append(dict(r))

                return {
                    "success": True,
                    "table": safe_table,
                    "schema": "main",
                    "columns": col_names,
                    "rows": rows,
                    "row_count": len(rows),
                    "execution_time_ms": latency_ms
                }
