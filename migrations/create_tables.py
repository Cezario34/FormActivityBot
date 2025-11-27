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
                    await cursor.execute(
                        query="""
                        INSERT INTO forms (id, title, version, is_active)
                        VALUES (1, 'Основная анкета', 1, true)
                        ON CONFLICT (id) DO NOTHING;
                                                """
                    )
                    await cursor.execute(
                        query="""
                            INSERT INTO questions (form_id, short_name, text, q_type, sort_order, required, validation, options)
                            VALUES
                            -- 0
                            (1, 'ФИО',
                             'Введите ФИО полностью
                              Например: Иванов Иван Иванович',
                             'text', 0, true,
                             '{"min_len": 2, "max_len": 120}'::jsonb,
                             NULL),
                            
                            -- 1
                            (1, 'Телефон',
                             'Введите номер телефона
                              Например: +79123456789',
                             'phone', 1, true,
                             '{"regex": "^\\\\+?7\\\\d{10}$"}'::jsonb,
                             NULL),
                            
                            -- 2
                            (1, 'Звание',
                             'Введите звание
                             Например: Рядовой',
                             'text', 2, true,
                             '{"min_len": 1, "max_len": 150}'::jsonb,
                             NULL),
                            
                            -- 3
                            (1, 'Должность',
                             'Введите должность
                              Например:Связист',
                             'text', 3, true,
                             '{"min_len": 1, "max_len": 150}'::jsonb,
                             NULL),
                            
                            -- 4
                            (1, 'Подразделение',
                             'Введите подразделение:
                             Например:2 подразделение',
                             'text', 4, true,
                             '{"min_len": 1, "max_len": 150}'::jsonb,
                             NULL),
                            
                            -- 6
                            (1, 'Взвод',
                             'Выберите взвод',
                             'choice', 6, true,
                             NULL,
                             ARRAY['1 вз', '2 вз', '3 вз']),
                            
                            -- 7
                            (1, 'Дата рождения',
                             'Введите день рождения(дд.мм.гггг)
                             Например: 27.12.1990',
                             'date', 7, true,
                             '{"format": "dd.mm.yyyy", "min_age": 16, "max_age": 70}'::jsonb,
                             NULL),
                            
                            -- 8
                            (1, 'Модель бейджика',
                             'Введите модель бейджика.
                             Например: хххх-хххх',
                             'choice', 8, true,
                             NULL,
                             ARRAY['1', '2', '3']),
                            
                            -- 9
                            (1, 'Номер бейджика',
                             'Введите номер прикрепленного бейджика.
                             Например: хххх-хххх',
                             'text', 9, true,
                             '{"min_len": 1, "max_len": 150}'::jsonb,
                             NULL),
                            
                            -- 10
                            (1, 'Размер головы',
                             'Введите размер головы.
                             Например: 50',
                             'number', 10, true,
                             '{"min": 10, "max": 100}'::jsonb,
                             NULL),
                            
                            -- 11
                            (1, 'Размер одежды',
                             'Введите размер одежды
                             Например: 50',
                             'number', 11, true,
                             '{"min_len": 1, "max_len": 250}'::jsonb,
                             NULL),
                            
                            -- 12
                            (1, 'Рост',
                             'Введите рост (см)
                             Например: 180',
                             'number', 12, true,
                             '{"min": 110, "max": 330}'::jsonb,
                             NULL),
                            
                            -- 13
                            (1, 'Размер обуви',
                             'Введите размер обуви
                             Например: 43',
                             'number', 13, true,
                             '{"min": 15, "max": 95}'::jsonb,
                             NULL);

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
