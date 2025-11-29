import logging
from contextlib import suppress

from aiogram import Bot, Router, F
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import KICKED, ChatMemberUpdatedFilter, Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from app.bot.enums.roles import UserRole
from app.bot.keyboards.menu_button import get_main_menu_commands
from aiogram.types import BotCommandScopeChat, ChatMemberUpdated, Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.bot.keyboards.keyboard import create_kb, keyboard_answer
from app.bot.keyboards.info_kb import build_kb
from app.infrastructure.database.db import (
    add_user,
    get_user,
    save_answer,
    get_question_by_order,
    get_first_question,
    get_active_form,
    get_next_question_db, get_all_answer, set_target_answer
    )
from aiogram.fsm.state import default_state, State, StatesGroup
from app.bot.modules.modules import load_form_json, get_question, \
    extract_answer, get_next_question
from psycopg.connection_async import AsyncConnection

from app.bot.lexicon.lexicon import LEXICON_RU
from app.bot.states.states import FormFilling, EditFillform

logger = logging.getLogger(__name__)

user_router = Router()



@user_router.message(CommandStart())
@user_router.message(F.text == LEXICON_RU['/restart'])
async def process_start_command(
        message: Message,
        conn: AsyncConnection,
        bot: Bot,
        LEXICON_RU: dict[str, str],
        state: FSMContext,
        admin_ids: list[int],
        ):


    user_row = await get_user(conn, tg_id=message.from_user.id)
    if message.from_user.id in admin_ids:
        user_role = UserRole.ADMIN

    else:
        user_role = UserRole.USER
    if user_row is None:
        if message.from_user.id in admin_ids:
            user_role = UserRole.ADMIN
        else:
            user_role = UserRole.USER
        await add_user(
            conn,
            tg_id=message.from_user.id,
            role=user_role
            )
    else:
        user_role = UserRole(user_row[2])

    lexicon_kb = build_kb(user_role)

    await bot.set_my_commands(
        commands=get_main_menu_commands(LEXICON_RU=LEXICON_RU, role=user_role),
        scope=BotCommandScopeChat(
            type=BotCommandScopeType.CHAT,
            chat_id=message.from_user.id
            )
        )

    await message.answer(text=LEXICON_RU.get("/start"),
                         reply_markup=create_kb(lexicon_kb, width=2))
    await state.clear()


@user_router.message(Command(commands="help"))
@user_router.message(F.text == LEXICON_RU['/help_command'])
async def process_help_command(message: Message, LEXICON_RU: dict[str, str]):
    await message.answer(text=LEXICON_RU.get("/help"))



@user_router.message(Command(commands='cancel'), StateFilter(default_state))
@user_router.message(F.text == "Отменить заполнение", StateFilter(default_state))
async def process_cancel_command(message: Message):
    await message.answer(
        text='Отменять нечего. Вы вне заполнения анкеты\n\n'
             'Чтобы перейти к заполнению анкеты - '
             'отправьте команду /fillform'
    )

@user_router.message(Command(commands="cancel"), ~StateFilter(default_state))
@user_router.message(F.text == "Отменить заполнение", ~StateFilter(default_state))
async def cancel_form(message: Message, state: FSMContext):
    await message.answer(
        text='Вы вышли из заполнения анкеты\n\n'
             'Чтобы снова перейти к заполнению анкеты - '
             'отправьте команду /fillform'
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()


@user_router.message(Command(commands="fillform"))
@user_router.message(F.text == "Заполнить анкету")
async def start_form(message: Message, state: FSMContext, conn: AsyncConnection):

    form = await get_active_form(conn)
    if not form:
        await message.answer("Активной анкеты нет. Сообщите администратору.")
        return

    # 2) первый вопрос
    first_q = await get_first_question(conn, form["id"])
    if not first_q:
        await message.answer("В активной анкете нет вопросов. Сообщите администратору.")
        return

    # 3) сохраняем контекст прохождения
    await state.update_data(
        form_id=form["id"],
        form_version=form["version"],
        current_order=first_q["sort_order"],# <-- это теперь sort_order
        answers={},
    )

    # 4) задаём первый вопрос
    await message.answer(
        first_q["text"],
        reply_markup=keyboard_answer(first_q)  # <-- клава по options
    )
    await state.set_state(FormFilling.answer)



@user_router.message(FormFilling.answer)
async def handle_answer(message: Message, state: FSMContext, conn: AsyncConnection):
    data = await state.get_data()

    form_id = data["form_id"]
    cur_order = data["current_order"]

    cur_q = await get_question_by_order(conn, form_id, cur_order)
    if not cur_q:
        await message.answer("Текущий вопрос не найден. Сообщите администратору.")
        await state.clear()
        return


    answer, error = extract_answer(message, cur_q)
    if error:
        await message.answer(error)
        await message.answer(cur_q["text"], reply_markup=keyboard_answer(cur_q))
        return

    answers = data.get("answers", {})
    q_id = cur_q["id"]
    answers[q_id] = {"short_name": cur_q["short_name"], "answer": answer}
    await state.update_data(answers=answers)

    # 4) берём следующий вопрос по sort_order
    next_q = await get_next_question_db(conn, form_id, cur_order)

    # 5) если вопросов больше нет — сохраняем пакетно и завершаем
    if not next_q:
        await save_answer(
            conn=conn,
            tg_id=message.from_user.id,
            answers=answers,
        )
        await message.answer("Спасибо! Анкета завершена.")
        await state.clear()
        return

    # 6) иначе — обновляем current_order и задаём следующий вопрос
    await state.update_data(current_order=next_q["sort_order"])
    await message.answer(
        next_q["text"],
        reply_markup=keyboard_answer(next_q)
    )

@user_router.message(Command(commands='edit_fill'), StateFilter(default_state))
@user_router.message(F.text == "Редактировать мою анкету", StateFilter(default_state))
async def edit_fillform(message: Message, state: FSMContext, conn: AsyncConnection):
    answers = await get_all_answer(conn=conn, tg_id=message.from_user.id)
    if not answers:
        await message.answer('Вы еще не прошли анкету')
        return
    lines = []
    for i, row in enumerate(answers):
        lines.append(f'{i+1}. {row['question_text']}\n'
                     f'Ответ: {row["answer_text"]}')
    await message.answer('\n\n'.join(lines))
    await state.update_data(
        answers_map=[
            {
                "answer_id": row["id"],
                "question_id": row["question_id"],
                'answer_text': row["answer_text"],
            }
            for row in answers
        ]
    )
    await message.answer('Введите номер вопроса, который вы хотите изменить')
    await state.set_state(EditFillform.choise_question)

@user_router.message(EditFillform.choise_question)
async def edit_fillform(message: Message, state: FSMContext, conn: AsyncConnection):
    num_answ = message.text.strip()
    if not num_answ:
        await message.answer("Введите число")
        return

    try:
        num = int(num_answ)
    except ValueError:
        await message.answer("Нужно ввести именно число, например: 1")
        return

    data = await state.get_data()
    answer_map = data.get("answers_map", [])

    if not answer_map:
        await message.answer("Не удалось найти список ответов попробуйте еще раз")
        await state.clear()
        return

    if not (1 <= num <= len(answer_map)):
        await message.answer(f'Нужно число от 1 до {len(answer_map)}')
        return

    target = answer_map[num - 1]
    await state.update_data(
        target_question_id = target["question_id"],)

    await message.answer("Введите новый ответ для выбранного вопроса")
    await state.set_state(EditFillform.new_answer)

@user_router.message(EditFillform.new_answer)
async def edit_fillform_new_answer(message: Message, state: FSMContext, conn: AsyncConnection):
    new_answer = message.text.strip()
    if not new_answer:
        await message.answer("Ответ не может быть пустым, введите заново")
        return

    data = await state.get_data()
    question_id = data.get("target_question_id")

    if not question_id:
        await message.answer("Техническая ошибка: не найден id ответа. Попробуйте начать редактирование заново.")
        await state.clear()
        return

    print(new_answer, message.from_user.id, question_id)
    await set_target_answer(conn, new_answer, message.from_user.id, question_id)
    await message.answer("✅ Ответ обновлён.")
    await state.clear()