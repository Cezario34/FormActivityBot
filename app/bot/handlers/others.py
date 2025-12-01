import logging
from contextlib import suppress

from aiogram import Bot, Router
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import KICKED, ChatMemberUpdatedFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, ChatMemberUpdated, Message
from psycopg import AsyncConnection
from aiogram.filters import Command, StateFilter

from app.bot.enums.roles import UserRole
from app.bot.filters.filters import UserRoleFilter
from app.bot.states.states import SwtitchRole
from app.infrastructure.database.dev_panels import edit_role

logger = logging.getLogger(__name__)

others_router = Router()
others_router.message.filter(UserRoleFilter(UserRole.DEVELOPER))


@others_router.message(Command(commands=["change_role"]))
async def change_role_start(message: Message, state: FSMContext):
    await message.answer(
        "Введите tg_id пользователя, роль которого нужно изменить\n"
        "Или напишите 'отмена' для отмены."
    )
    await state.set_state(SwtitchRole.editrole)


@others_router.message(SwtitchRole.editrole)
async def change_role_get_tg_id(message: Message, state: FSMContext):
    text = (message.text or "").strip().lower()

    if text in {"отмена", "cancel", "-"}:
        await state.clear()
        await message.answer("Изменение роли отменено.")
        return

    if not text.isdigit():
        await message.answer("Нужно ввести числовой tg_id или 'отмена'.")
        return

    target_tg_id = int(text)
    await state.update_data(target_tg_id=target_tg_id)

    await message.answer(
        "Введите новую роль для этого пользователя:\n"
        "`user`, `admin` или `developer`",
        parse_mode="Markdown",
    )
    await state.set_state(SwtitchRole.wait_role)


@others_router.message(SwtitchRole.wait_role)
async def change_role_set_role(message: Message, conn: AsyncConnection, state: FSMContext):
    text = (message.text or "").strip().lower()

    if text in {"отмена", "cancel", "-"}:
        await state.clear()
        await message.answer("Изменение роли отменено.")
        return

    if text not in {"user", "admin", "developer"}:
        await message.answer("Нужно ввести одну из ролей: user, admin, developer.")
        return

    data = await state.get_data()
    target_tg_id = data.get("target_tg_id")

    if not target_tg_id:
        await state.clear()
        await message.answer("tg_id потерялся, начните заново командой /change_role.")
        return

    ok = await edit_role(conn, target_tg_id, text)

    await state.clear()

    if ok:
        await message.answer(f"Роль пользователя {target_tg_id} изменена на {text}.")
    else:
        await message.answer("Пользователь с таким tg_id не найден в базе.")



