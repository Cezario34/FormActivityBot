import logging
from datetime import datetime, timezone
from typing import Any

from app.bot.enums.roles import UserRole
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Json

logger = logging.getLogger(__name__)


async def add_question(
    conn: AsyncConnection,
    *,
    form_id: int,
    short_name: str,
    text: str,
    q_type: str,
    required: bool = True,
    validation: dict[str, Any] | None = None,
    options: list[str] | None = None,
) -> int:
    if validation is not None:
        validation_param = Json(validation)   # dict -> JSON для postgres
    else:
        validation_param = None
    async with conn.cursor() as cur:
        await cur.execute("""
            WITH next_order AS (
                SELECT COALESCE(MAX(sort_order), -1) + 1 AS so
                FROM questions
                WHERE form_id = %s
            )
            INSERT INTO questions(
                form_id, short_name, text, q_type, sort_order, required, validation, options, is_active
            )
            SELECT
                %s, %s, %s, %s, next_order.so, %s, %s, %s::text[], true
            FROM next_order
            RETURNING id, sort_order;
        """, (
            form_id,
            form_id, short_name, text, q_type, required,
            validation_param, options
        ))
        new_id, so = await cur.fetchone()
    return new_id

async def delete_question(conn: AsyncConnection, q_id: int) -> bool:
    """
    Удаляет вопрос по id.
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "DELETE FROM answers WHERE question_id = %s;",
            (str(q_id),),   # важно: str(q_id), т.к. колонка TEXT
        )
    async with conn.cursor() as cur:
        await cur.execute(
            "DELETE FROM questions WHERE id = %s RETURNING id;",
            (q_id,),
        )
        row = await cur.fetchone()

    return row is not None

async def get_active_questions(conn: AsyncConnection, form_id: int = 1) -> list[dict[str, Any]]:
    """
    Возвращает список АКТИВНЫХ вопросов формы.
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT id, sort_order, short_name, q_type, required
            FROM questions
            WHERE form_id = %s AND is_active = true
            ORDER BY sort_order;
            """,
            (form_id,),
        )
        return await cur.fetchall()

async def check_question(conn: AsyncConnection, q_id: int) -> dict[str, Any] | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT id, short_name, sort_order, text
            FROM questions
            WHERE id = %s;
            """,
            (q_id,),
        )
        row = await cur.fetchone()
    return row


ALLOWED_QUESTION_FIELDS = {
    "short_name",
    "text",
    "required",
    "options",
    "validation",
}

async def update_question(
    conn: AsyncConnection,
    q_id: int,
    **fields: Any,
) -> None:

    clean_fields: dict[str, Any] = {}

    for k, v in fields.items():
        if k not in ALLOWED_QUESTION_FIELDS:
            continue

        if k == "validation":
            # validation учитываем всегда, даже если None
            clean_fields[k] = v
        else:
            # остальные поля: None = "не обновлять"
            if v is not None:
                clean_fields[k] = v

    if not clean_fields:
        return

    set_clauses: list[str] = []
    params: list[Any] = []

    for column, value in clean_fields.items():
        if column == "validation" and value is not None:
            value = Json(value)

        set_clauses.append(f"{column} = %s")
        params.append(value)

    params.append(q_id)
    logger.debug(params)
    logger.debug(clean_fields)
    query = f"""
        UPDATE questions
        SET {', '.join(set_clauses)}
        WHERE id = %s;
    """

    async with conn.cursor() as cur:
        await cur.execute(query, params)