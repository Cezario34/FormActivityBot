import logging
from datetime import datetime, timezone
from typing import Any

from app.bot.enums.roles import UserRole
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Json


async def edit_role(conn: AsyncConnection, tg_id: int, user_role: UserRole | str) -> bool:
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE users SET role = %s WHERE tg_id = %s RETURNING tg_id;",
            (user_role.value, tg_id),
        )
        row = await cur.fetchone()

    return row is not None
