import logging

import psycopg_pool
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from app.bot.handlers.admin import admin_router
from app.bot.handlers.others import others_router
from app.bot.handlers.settings import settings_router
from app.bot.handlers.user import user_router
from app.bot.lexicon.lexicon import LEXICON_RU
from app.bot.middlewares.database import DataBaseMiddleware
# from app.bot.middlewares.LEXICON_RU import TranslatorMiddleware
# from app.bot.middlewares.lang_settings import LangSettingsMiddleware
# from app.bot.middlewares.shadow_ban import ShadowBanMiddleware
# from app.bot.middlewares.statistics import ActivityCounterMiddleware
from app.infrastructure.database.connections import get_pg_pool
from config.config import Config
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


# Функция конфигурирования и запуска бота
async def main(config: Config) -> None:
    logger.info("Starting bot...")
    # Инициализируем хранилище
    redis = RedisStorage(
        redis=Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            username=config.redis.username,
        )
    )
    storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True))

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Создаём пул соединений с Postgres
    db_pool: psycopg_pool.AsyncConnectionPool = await get_pg_pool(
        db_name=config.db.name,
        host=config.db.host,
        port=config.db.port,
        user=config.db.user,
        password=config.db.password,
    )


    logger.info("Including routers...")
    dp.include_routers(settings_router, admin_router, user_router, others_router)
    dp.update.middleware(DataBaseMiddleware())
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем поллинг
    try:
        await dp.start_polling(
            bot,
            db_pool=db_pool,
            LEXICON_RU=LEXICON_RU,
            developer_ids=config.bot.developer_ids
        )
    except Exception as e:
        logger.exception(e)
    finally:
        # Закрываем пул соединений
        await db_pool.close()
        logger.info("Connection to Postgres closed")
