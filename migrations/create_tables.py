import asyncio
import logging
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
from app.infrastructure.database.connections import get_pg_connection
from config.config import Config, load_config
from psycopg import AsyncConnection, Error

config: Config = load_config()

logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

logger = logging.getLogger(__name__)

if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    connection: AsyncConnection | None = None

    try:
        connection = await get_pg_connection(
            db_name=config.db.name,
            host=config.db.host,
            port=config.db.port,
            user=config.db.user,
            password=config.db.password,
        )
        async with connection:
            async with connection.transaction():
                async with connection.cursor() as cursor:

                    # ---------------- USERS ----------------
                    await cursor.execute(
                        query="""
                            CREATE TABLE IF NOT EXISTS users(
                                id BIGSERIAL PRIMARY KEY,
                                tg_id BIGINT NOT NULL UNIQUE,              -- telegram user id
                                role VARCHAR(50),
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                banned BOOLEAN NOT NULL DEFAULT FALSE
                            );
                        """
                    )

                    # ---------------- FORMS ----------------
                    await cursor.execute(
                        query="""
                        DROP TABLE IF EXISTS forms CASCADE;
                            CREATE TABLE IF NOT EXISTS forms (
                                id SERIAL PRIMARY KEY,
                                title TEXT NOT NULL,
                                version INT NOT NULL DEFAULT 1,
                                is_active BOOLEAN NOT NULL DEFAULT true,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                        """
                    )

                    # ---------------- QUESTIONS ----------------
                    await cursor.execute(
                        query="""
                        DROP TABLE IF EXISTS questions CASCADE;
                            CREATE TABLE questions (
                                id SERIAL PRIMARY KEY,
                                form_id INT NOT NULL REFERENCES forms(id),
                                short_name TEXT NOT NULL,        -- Новое поле ► "номер обуви", "ФИО"
                                text TEXT NOT NULL,              -- Полный текст вопроса (для бота)
                                q_type TEXT NOT NULL,            -- text/number/date/choice/phone...
                                sort_order INT NOT NULL,            -- Порядок
                                required BOOLEAN NOT NULL,
                                validation JSONB,                -- Храним любые правила
                                options TEXT[] DEFAULT NULL,     -- Для choice
                                is_active BOOLEAN NOT NULL DEFAULT true
                            );
                        """
                    )

                    # ---------------- ANSWERS ----------------
                    await cursor.execute(
                        query="""
                        DROP TABLE IF EXISTS answers CASCADE;
                            CREATE TABLE IF NOT EXISTS answers(
                                id BIGSERIAL PRIMARY KEY,
                                tg_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
                                question_id TEXT NOT NULL,
                                question_text TEXT NOT NULL,
                                answer_text TEXT NOT NULL,
                                answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                UNIQUE(tg_id, question_id)
                            );

                            CREATE INDEX IF NOT EXISTS idx_answers_user_form
                            ON answers(tg_id, question_id);

                            CREATE INDEX IF NOT EXISTS idx_answers_question
                            ON answers(question_id);
                        """
                    )

                logger.info("Tables `users`, `activity`, `forms`, `questions`, `answers` were successfully created")

    except Error as db_error:
        logger.exception("Database-specific error: %s", db_error)
    except Exception as e:
        logger.exception("Unhandled error: %s", e)
    finally:
        if connection:
            await connection.close()
            logger.info("Connection to Postgres closed")


asyncio.run(main())
