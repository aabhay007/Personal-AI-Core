"""PostgreSQL Database Connector using asyncpg."""
import time
import logging
from typing import Any, Dict, List, Optional
import asyncpg
from app.integrations.base import BaseDatabaseConnector, validate_identifier

logger = logging.getLogger(__name__)


class PostgresConnector(BaseDatabaseConnector):
    """PostgreSQL implementation supporting connection testing, introspection, and safe read-only queries."""

    def __init__(
        self,
        host: str,
        port: int = 5432,
        database: str = "postgres",
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssl_mode: str = "prefer",
        timeout: int = 5
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.ssl_mode = ssl_mode
        self.timeout = timeout

    def _get_ssl_setting(self) -> Any:
        if self.ssl_mode in ("disable", "false", "no"):
            return False
        if self.ssl_mode in ("require", "true", "yes"):
            return True
        return "prefer"

    async def _get_connection(self) -> asyncpg.Connection:
        ssl_setting = self._get_ssl_setting()
        return await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.database,
            ssl=ssl_setting,
            timeout=self.timeout
        )

    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity and measure round-trip latency."""
        start_time = time.perf_counter()
        conn = None
        try:
            conn = await self._get_connection()
            version = await conn.fetchval("SELECT version();")
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": True,
                "latency_ms": latency_ms,
                "version": str(version),
                "database": self.database,
                "error": None
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"PostgreSQL connection test failed: {e}")
            return {
                "success": False,
                "latency_ms": latency_ms,
                "version": None,
                "database": self.database,
                "error": str(e)
            }
        finally:
            if conn:
                await conn.close()

    async def get_schemas(self) -> List[str]:
        """Retrieve accessible database schemas excluding internal catalogs."""
        conn = await self._get_connection()
        try:
            query = """
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name;
            """
            rows = await conn.fetch(query)
            return [r["schema_name"] for r in rows]
        finally:
            await conn.close()

    async def get_tables(self, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Introspect tables, columns, data types, and primary keys for the schema."""
        target_schema = validate_identifier(schema_name or "public", "schema name")
        conn = await self._get_connection()
        try:
            # Query base tables
            tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = $1 AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """
            table_rows = await conn.fetch(tables_query, target_schema)

            # Query columns
            columns_query = """
                SELECT table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = $1
                ORDER BY table_name, ordinal_position;
            """
            column_rows = await conn.fetch(columns_query, target_schema)

            # Query primary keys
            pk_query = """
                SELECT kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = $1 AND tc.constraint_type = 'PRIMARY KEY';
            """
            pk_rows = await conn.fetch(pk_query, target_schema)

            pk_map = set((r["table_name"], r["column_name"]) for r in pk_rows)

            columns_by_table: Dict[str, List[Dict[str, Any]]] = {}
            for col in column_rows:
                t_name = col["table_name"]
                if t_name not in columns_by_table:
                    columns_by_table[t_name] = []
                columns_by_table[t_name].append({
                    "name": col["column_name"],
                    "data_type": col["data_type"],
                    "is_nullable": col["is_nullable"] == "YES",
                    "is_primary_key": (t_name, col["column_name"]) in pk_map,
                    "default": col["column_default"]
                })

            result = []
            for t in table_rows:
                t_name = t["table_name"]
                result.append({
                    "table_name": t_name,
                    "schema": target_schema,
                    "columns": columns_by_table.get(t_name, [])
                })

            return result
        finally:
            await conn.close()

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
        """Safely build and execute a parameterized read-only query on PostgreSQL."""
        safe_schema = validate_identifier(schema_name or "public", "schema name")
        safe_table = validate_identifier(table, "table name")

        # Validate columns
        if columns and len(columns) > 0:
            safe_cols = [validate_identifier(c, "column name") for c in columns]
            cols_clause = ", ".join(f'"{c}"' for c in safe_cols)
        else:
            cols_clause = "*"

        # Validate and parameterize filters
        where_clauses = []
        params = []
        param_idx = 1

        if filters:
            for col_name, val in filters.items():
                safe_col = validate_identifier(col_name, "filter column")
                where_clauses.append(f'"{safe_col}" = ${param_idx}')
                params.append(val)
                param_idx += 1

        where_stmt = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Validate order by
        order_stmt = ""
        if order_by:
            safe_order = validate_identifier(order_by, "order_by column")
            direction = "DESC" if order_desc else "ASC"
            order_stmt = f'ORDER BY "{safe_order}" {direction}'

        # Restrict limit (max 100)
        safe_limit = min(max(1, limit), 100)
        safe_offset = max(0, offset)

        limit_clause = f"LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([safe_limit, safe_offset])

        query = f'SELECT {cols_clause} FROM "{safe_schema}"."{safe_table}" {where_stmt} {order_stmt} {limit_clause};'

        start_time = time.perf_counter()
        conn = await self._get_connection()
        try:
            # Set session to READ ONLY transaction for extra defense in depth
            tr = conn.transaction(readonly=True)
            await tr.start()
            try:
                records = await conn.fetch(query, *params)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                rows = []
                col_names = []
                if records:
                    col_names = list(records[0].keys())
                    for r in records:
                        row_dict = {}
                        for k, v in dict(r).items():
                            row_dict[k] = str(v) if v is not None and not isinstance(v, (int, float, bool, str, list, dict)) else v
                        rows.append(row_dict)

                return {
                    "success": True,
                    "table": safe_table,
                    "schema": safe_schema,
                    "columns": col_names,
                    "rows": rows,
                    "row_count": len(rows),
                    "execution_time_ms": latency_ms
                }
            finally:
                await tr.rollback()
        finally:
            await conn.close()
