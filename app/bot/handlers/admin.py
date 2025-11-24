import logging
from contextlib import suppress

from aiogram import Bot, Router, F
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from psycopg import AsyncConnection

from app.bot.enums.roles import UserRole
from app.bot.filters.filters import  UserRoleFilter
from app.bot.keyboards.keyboard import keyboard_answer, create_kb
from app.bot.lexicon.lexicon import LEXICON_RU
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, ChatMemberUpdated, Message
from app.bot.modules.modules import rows_to_csv_bytes
from app.infrastructure.database.db import get_all_answers
from aiogram.types import BufferedInputFile
from app.bot.helper_dict.helper_dict import edit_form_dict
from aiogram.fsm.state import default_state
from app.bot.states.states import EditAnswer

logger = logging.getLogger(__name__)

admin_router = Router()
admin_router.message.filter(UserRoleFilter(UserRole.ADMIN))

@admin_router.message(Command(commands='help'))
@admin_router.message(F.text == 'Справка')
async def statistics(message: Message, conn:  AsyncConnection, LEXICON_RU: dict[str, str],):
    await message.answer(text=LEXICON_RU.get('/help_admin'))

@admin_router.message(Command(commands="statistics"))
@admin_router.message(F.text == LEXICON_RU['statistic_csv'])
async def statistics(message: Message, conn: AsyncConnection):
    rows = await get_all_answers(conn)
    csv_bytes = rows_to_csv_bytes(rows)

    file = BufferedInputFile(csv_bytes, filename="answers.csv")
    await message.answer_document(file, caption="Статистика ответов")


@admin_router.message(Command(commands="cancel_edit"), ~StateFilter(default_state))
@admin_router.message(F.text == "Выйти из меню редактированию", ~StateFilter(default_state))
async def cancel_form(message: Message, state: FSMContext):
    await message.answer(
        text='Вы вышли из меню редактора\n\n'
             'Чтобы снова перейти к редактированию - '
             'отправьте команду /edit'
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()


@admin_router.message(Command(commands="cancel_edit"), StateFilter(default_state))
@admin_router.message(F.text == "Выйти из меню редактированию", StateFilter(default_state))
async def cancel_form(message: Message, state: FSMContext):
    await message.answer(
        text='Вы сейчас ничего не редактируете'
    )



@admin_router.message(Command(commands="edit"))
@admin_router.message(F.text == LEXICON_RU['/edit'],)
async def statistics(message: Message, state: FSMContext):
    await message.answer(text=LEXICON_RU['/edit_answer'],
                         reply_markup=create_kb(edit_form_dict))
    await state.set_state(EditAnswer.edit_answer)


@admin_router.message(F.text == LEXICON_RU['delete_question'], EditAnswer.edit_answer)
async def statistics(message: Message):
    await message.answer(text='Меню удаления вопроса',
                         reply_markup=create_kb(edit_form_dict))


@admin_router.message(F.text == LEXICON_RU['edit_question'], EditAnswer.edit_answer)
async def statistics(message: Message):
    await message.answer(text='Меню изменения вопроса',
                         )

@admin_router.message(F.text == LEXICON_RU['add_question'], EditAnswer.edit_answer)
async def statistics(message: Message):
    await message.answer(text="Меню добавления вопроса")