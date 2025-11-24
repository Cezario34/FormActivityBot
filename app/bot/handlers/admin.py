import logging
from contextlib import suppress

from aiogram import Bot, Router, F
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from psycopg import AsyncConnection

from app.bot.enums.roles import UserRole
from app.bot.filters.filters import  UserRoleFilter
from app.bot.lexicon.lexicon import LEXICON_RU
from aiogram.filters import KICKED, ChatMemberUpdatedFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, ChatMemberUpdated, Message
from app.bot.modules.modules import rows_to_csv_bytes
from app.infrastructure.database.db import get_all_answers
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

admin_router = Router()
admin_router.message.filter(UserRoleFilter(UserRole.ADMIN))
# #
@admin_router.message(Command(commands='help'))
@admin_router.message(F.text == 'Справка')
async def statistics(message: Message, conn:  AsyncConnection, LEXICON_RU: dict[str, str],):
    await message.answer(text=LEXICON_RU.get('/help_admin'))


@admin_router.message(Command("statistics"))
async def statistics(message: Message, conn: AsyncConnection):
    rows = await get_all_answers(conn)
    csv_bytes = rows_to_csv_bytes(rows)

    file = BufferedInputFile(csv_bytes, filename="answers.csv")
    await message.answer_document(file, caption="Статистика ответов")