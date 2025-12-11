from psycopg.connection_async import AsyncConnection
from app.bot.enums.roles import UserRole
from app.infrastructure.database.db import (
    get_user,
    add_user,)
from app.infrastructure.database.dev_panels import edit_role

async def create_user_and_role(conn: AsyncConnection, tg_id: int, developer_ids: [list]) -> UserRole:
    user_row = await get_user(conn, tg_id=tg_id)

    if user_row is None:
        if tg_id in developer_ids:
            user_role = UserRole.DEVELOPER

        else:
            user_role = UserRole.USER
        await add_user(
            conn,
            tg_id=tg_id,
            role=user_role
            )
    else:
        user_role = UserRole(user_row[2])
    if tg_id in developer_ids and user_role != UserRole.DEVELOPER:
        user_role = UserRole.DEVELOPER
        await edit_role(conn, tg_id, UserRole.ADMIN)
    return user_role