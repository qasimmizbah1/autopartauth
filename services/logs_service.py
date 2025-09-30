# services/logging.py
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Request
import json

async def write_log(
    request: Request,
    *,
    action: str,
    level: str = "INFO",
    user_id: Optional[UUID] = None,
    path: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
):
    

    if path is None and request:
        path = request.url.path
    if ip is None and request:
        ip = request.client.host if request.client else None
    if user_agent is None and request:
        user_agent = request.headers.get("user-agent")

    meta_json = json.dumps(meta) if meta else "{}"

    async with request.app.state.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO system_log (user_id, level, action, path, ip, user_agent, meta)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            str(user_id) if user_id else None,
            level,
            action,
            path,
            ip,
            user_agent,
            meta_json,
        )
