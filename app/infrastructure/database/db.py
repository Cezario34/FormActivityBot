import logging
from datetime import datetime, timezone
from typing import Any

from app.bot.enums.roles import UserRole
from psycopg import AsyncConnection
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

async def add_user(
    conn: AsyncConnection,
    *,
    tg_id: int,
    username: str | None = None,
    role: UserRole = UserRole.USER,
    banned: bool = False,
) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="""
                INSERT INTO users(tg_id, role, banned)
                VALUES(
                    %(tg_id)s, 
                    %(role)s, 
                    %(banned)s
                ) ON CONFLICT DO NOTHING;
            """,
            params={
                "tg_id": tg_id,
                "username": username,
                "role": role,
                "banned": banned,
            },
        )
    logger.info(
        "User added. Table=`%s`, tg_id=%d, created_at='%s', role=%s,  banned=%s",
        "users",
        tg_id,
        datetime.now(timezone.utc),
        role,
        banned,
    )

async def get_user(
    conn: AsyncConnection,
    *,
    tg_id: int,
) -> tuple[Any, ...] | None:
    async with conn.cursor() as cursor:
        data = await cursor.execute(
            query="""
                SELECT 
                    id,
                    tg_id,
                    role,
                    banned,
                    created_at
                    FROM users WHERE tg_id = %s;
            """,
            params=(tg_id,),
        )
        row = await data.fetchone()
    logger.info("Row is %s", row)
    return row if row else None


async def save_answer(
    conn: AsyncConnection,
    *,
    tg_id: int,
    answers: dict[int, dict[str, Any]] | None = None,
):
    if not answers:
        return

    rows = [
        (
            tg_id,
            q_id,
            payload["short_name"],
            str(payload["answer"]),
        )
        for q_id, payload in answers.items()
    ]

    async with conn.cursor() as cursor:
        await cursor.executemany(
            query="""
                INSERT INTO answers(tg_id, question_id, question_text, answer_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (tg_id, question_id)
                DO UPDATE SET
                    question_text = EXCLUDED.question_text,
                    answer_text = EXCLUDED.answer_text,
                    answered_at = NOW();
            """,
            params_seq=rows,
        )


async def get_user_role(
    conn: AsyncConnection,
    *,
    tg_id: int,
) -> UserRole | None:
    async with conn.cursor() as cursor:
        data = await cursor.execute(
            query="""
                SELECT role FROM users WHERE tg_id = %s;
            """,
            params=(tg_id,),
        )
        row = await data.fetchone()
    if row:
        logger.info("The user with `tg_id`=%s has the role is %s", tg_id, row[0])
    else:
        logger.warning("No user with `tg_id`=%s found in the database", tg_id)
    return UserRole(row[0]) if row else None

async def get_all_answers(
    conn: AsyncConnection,
) -> list[dict[str, Any]]:
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            """
            SELECT a.*,
                   u.role
            FROM answers a
                     LEFT JOIN users u ON u.tg_id = a.tg_id
            ORDER BY a.answered_at;
                             """
            )
        rows = await cursor.fetchall()
    return rows



async def get_active_form(conn: AsyncConnection) -> dict[str, Any] | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT id, title, version
            FROM forms
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT 1;
        """)
        return await cur.fetchone()


async def get_first_question(conn: AsyncConnection, form_id: int) -> dict[str, Any] | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT *
            FROM questions
            WHERE form_id=%s AND is_active=true
            ORDER BY sort_order
            LIMIT 1;
        """, (form_id,))
        return await cur.fetchone()


async def get_question_by_order(conn: AsyncConnection, form_id: int, sort_order: int) -> dict[str, Any] | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT *
            FROM questions
            WHERE form_id=%s AND is_active=true AND sort_order=%s
            LIMIT 1;
        """, (form_id, sort_order))
        return await cur.fetchone()


async def get_next_question_db(conn: AsyncConnection, form_id: int, current_order: int) -> dict[str, Any] | None:
    """Берём следующий вопрос по sort_order."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT *
            FROM questions
            WHERE form_id=%s AND is_active=true AND sort_order > %s
            ORDER BY sort_order
            LIMIT 1;
        """, (form_id, current_order))
        return await cur.fetchone()