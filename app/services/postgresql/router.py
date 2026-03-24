"""PostgreSQL service router for database operations."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserSecret
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.security import decrypt_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/postgresql", tags=["postgresql"])


class PostgreSQLExecuteRequest(BaseModel):
    """Request body for executing PostgreSQL operations."""
    operation: str
    params: Dict[str, Any]


async def _get_connection_string(db: AsyncSession, owner_id: UUID) -> str:
    """Fetch and decrypt PostgreSQL connection string."""
    result = await db.execute(
        select(UserSecret).where(
            UserSecret.owner_id == owner_id,
            UserSecret.secret_key == 'postgresql_connection_string'
        )
    )
    secret = result.scalar_one_or_none()

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PostgreSQL connection string not found. Please configure it in the node settings."
        )

    connection_string = decrypt_value(secret.encrypted_value)

    if not connection_string:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PostgreSQL connection string is empty. Please reset and re-enter it."
        )

    return connection_string


async def execute_query(connection_string: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a raw SQL query."""
    try:
        import asyncpg
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="asyncpg library not installed. Please install asyncpg package."
        )

    query = params.get('query')
    query_params = params.get('params', [])

    if not query:
        raise HTTPException(status_code=400, detail="'query' is required")

    try:
        conn = await asyncpg.connect(connection_string)
        try:
            # Determine if query is SELECT or mutation
            query_upper = query.strip().upper()
            is_select = query_upper.startswith('SELECT') or query_upper.startswith('WITH')

            if is_select:
                rows = await conn.fetch(query, *query_params)
                return {
                    "rows": [dict(row) for row in rows],
                    "row_count": len(rows)
                }
            else:
                result = await conn.execute(query, *query_params)
                return {
                    "result": result,
                    "message": f"Query executed successfully: {result}"
                }
        finally:
            await conn.close()
    except Exception as e:
        logger.exception("PostgreSQL query execution failed")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def select_rows(connection_string: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Select rows from a table."""
    try:
        import asyncpg
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="asyncpg library not installed. Please install asyncpg package."
        )

    table = params.get('table')
    columns = params.get('columns', '*')
    where = params.get('where')
    limit = params.get('limit')

    if not table:
        raise HTTPException(status_code=400, detail="'table' is required")

    query = f"SELECT {columns} FROM {table}"
    if where:
        query += f" WHERE {where}"
    if limit:
        query += f" LIMIT {limit}"

    try:
        conn = await asyncpg.connect(connection_string)
        try:
            rows = await conn.fetch(query)
            return {
                "rows": [dict(row) for row in rows],
                "row_count": len(rows)
            }
        finally:
            await conn.close()
    except Exception as e:
        logger.exception("PostgreSQL select failed")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def insert_row(connection_string: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a row into a table."""
    try:
        import asyncpg
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="asyncpg library not installed. Please install asyncpg package."
        )

    table = params.get('table')
    data = params.get('data')

    if not table or not data:
        raise HTTPException(status_code=400, detail="'table' and 'data' are required")

    if isinstance(data, str):
        import json
        data = json.loads(data)

    columns = list(data.keys())
    values = list(data.values())
    placeholders = ', '.join([f'${i+1}' for i in range(len(values))])

    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *"

    try:
        conn = await asyncpg.connect(connection_string)
        try:
            row = await conn.fetchrow(query, *values)
            return {
                "inserted_row": dict(row) if row else None,
                "message": "Row inserted successfully"
            }
        finally:
            await conn.close()
    except Exception as e:
        logger.exception("PostgreSQL insert failed")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def update_rows(connection_string: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Update rows in a table."""
    try:
        import asyncpg
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="asyncpg library not installed. Please install asyncpg package."
        )

    table = params.get('table')
    data = params.get('data')
    where = params.get('where')

    if not table or not data or not where:
        raise HTTPException(status_code=400, detail="'table', 'data', and 'where' are required")

    if isinstance(data, str):
        import json
        data = json.loads(data)

    set_clauses = [f"{key} = ${i+1}" for i, key in enumerate(data.keys())]
    values = list(data.values())

    query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where}"

    try:
        conn = await asyncpg.connect(connection_string)
        try:
            result = await conn.execute(query, *values)
            return {
                "result": result,
                "message": f"Update completed: {result}"
            }
        finally:
            await conn.close()
    except Exception as e:
        logger.exception("PostgreSQL update failed")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def delete_rows(connection_string: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Delete rows from a table."""
    try:
        import asyncpg
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="asyncpg library not installed. Please install asyncpg package."
        )

    table = params.get('table')
    where = params.get('where')

    if not table or not where:
        raise HTTPException(status_code=400, detail="'table' and 'where' are required for safety")

    query = f"DELETE FROM {table} WHERE {where}"

    try:
        conn = await asyncpg.connect(connection_string)
        try:
            result = await conn.execute(query)
            return {
                "result": result,
                "message": f"Delete completed: {result}"
            }
        finally:
            await conn.close()
    except Exception as e:
        logger.exception("PostgreSQL delete failed")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/execute")
@limiter.limit("30/minute")
async def execute_operation(
    request: Request,
    body: PostgreSQLExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a PostgreSQL operation."""
    connection_string = await _get_connection_string(db, current_user.id)

    operations = {
        'query': execute_query,
        'select': select_rows,
        'insert': insert_row,
        'update': update_rows,
        'delete': delete_rows,
    }

    operation_fn = operations.get(body.operation)
    if not operation_fn:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {body.operation}")

    try:
        result = await operation_fn(connection_string, body.params)
        return result
    except Exception as e:
        logger.exception(f"PostgreSQL operation failed: {body.operation}")
        raise HTTPException(status_code=500, detail=str(e))
