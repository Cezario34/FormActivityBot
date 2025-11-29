import logging
from contextlib import suppress

from aiogram import Bot, Router, F
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from psycopg import AsyncConnection

from app.bot.enums.roles import UserRole
from app.bot.filters.filters import  UserRoleFilter
from app.bot.keyboards.keyboard import keyboard_answer, create_kb, kb_q_types, \
    kb_required, kb_edit_fields
from app.bot.lexicon.lexicon import LEXICON_RU
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, ChatMemberUpdated, Message, \
    CallbackQuery
from app.bot.modules.modules import rows_to_csv_bytes
from app.infrastructure.database.db import get_all_answers, get_active_form
from aiogram.types import BufferedInputFile
from app.bot.helper_dict.helper_dict import edit_form_dict, VALIDATION_HINT
from aiogram.fsm.state import default_state
from app.bot.states.states import EditAnswer, DeleteQuestion, EditQuestion
from app.infrastructure.database.edit_answer_db import add_question, \
    get_active_questions, check_question, delete_question, update_question

logger = logging.getLogger(__name__)

admin_router = Router()
admin_router.message.filter(UserRoleFilter(UserRole.ADMIN))

@admin_router.message(Command(commands='help'))
@admin_router.message(F.text == 'Справка')
async def help_admins(message: Message, conn:  AsyncConnection, LEXICON_RU: dict[str, str],):
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
async def cancel_form_edit(message: Message, state: FSMContext):
    await message.answer(
        text='Вы сейчас ничего не редактируете'
    )



@admin_router.message(Command(commands="edit"))
@admin_router.message(F.text == LEXICON_RU['/edit'],)
async def get_menu_edit(message: Message, state: FSMContext):
    await message.answer(text=LEXICON_RU['/edit_answer'],
                         reply_markup=create_kb(edit_form_dict))


@admin_router.message(F.text == LEXICON_RU['delete_question'])
@admin_router.message(F.text == LEXICON_RU['edit_question'])
async def delete_or_edit_quest(message: Message, state: FSMContext, conn: AsyncConnection):
    form = await get_active_form(conn)
    if not form:
        await message.answer("Нет активной формы. Сначала создайте/активируйте анкету.")
        return

    questions = await get_active_questions(conn, form["id"])
    if not questions:
        await message.answer("В активной анкете нет вопросов.")
        return

    lines = ["Текущие вопросы анкеты:\n"]
    for q in questions:
        rid = q["id"]
        order = q["sort_order"]
        sn = q["short_name"]
        qt = q["q_type"]
        req = "обязат." if q["required"] else "необязат."
        lines.append(f"ID {rid:>3} | {sn} ({qt}, {req})")

    lines.append("\nОтправь *ID вопроса*, который нужно удалить или изменить.\n"
                 "Или отправь `/cancel_edit`, чтобы отменить.")
    text = "\n".join(lines)

    await message.answer(text)
    if message.text == LEXICON_RU['edit_question']:
        await state.set_state(EditQuestion.wait_id)
    else:
        await state.set_state(DeleteQuestion.wait_id)

@admin_router.message(EditQuestion.wait_id)
async def edit_question_wait_id(message: Message, state: FSMContext, conn: AsyncConnection):
    raw = message.text.strip()

    if not raw.isdigit():
        await message.answer("Нужно ввести числовой ID вопроса или '-' для отмены.")
        return

    q_id = int(raw)
    q = await check_question(conn, q_id)
    if not q:
        await message.answer("Вопрос с таким ID не найден. Введи другой ID или '-' для отмены.")
        return

    await state.update_data(q_id=q_id)  # запоминаем, что редактируем
    await state.set_state(EditQuestion.choose_field)

    await message.answer(
        f"Редактируем вопрос:\n"
        f"ID {q['id']} | #{q['sort_order']} | {q['short_name']}\n\n"
        f"Текст:\n{q['text']}\n\n"
        f"Выбери, что хочешь изменить:",
        reply_markup=kb_edit_fields()
    )

@admin_router.callback_query(EditQuestion.choose_field, F.data.startswith("eq:"))
async def edit_question_choose_field(cb: CallbackQuery, state: FSMContext):
    field = cb.data.split(":", 1)[1]  # short_name / text / required / options / validation
    await state.update_data(edit_field=field)

    # required оставим отдельным сценарием (через кнопки)
    if field == "required":
        await state.set_state(EditQuestion.edit_required)
        await cb.message.edit_text(
            "Сделать вопрос обязательным?",
            reply_markup=kb_required()
        )
    else:
        # ВСЕ остальные пойдут в один универсальный message-хендлер
        await state.set_state(EditQuestion.edit_value)

        if field == "short_name":
            prompt = "Введи новое короткое название вопроса (short_name)."
        elif field == "text":
            prompt = "Введи новый текст вопроса (как его увидит пользователь)."
        elif field == "options":
            prompt = (
                "Введи новые варианты ответа через запятую.\n\n"
                "Например:\n1 вз, 2 вз, 3 вз\n\n"
                "Если нужно очистить варианты — отправь '-'."
            )
        elif field == "validation":
            prompt = VALIDATION_HINT
        else:
            prompt = "Введи новое значение."

        await cb.message.edit_text(prompt)

    await cb.answer()

@admin_router.message(EditQuestion.edit_value)
async def edit_question_value(message: Message, state: FSMContext, conn: AsyncConnection):
    raw = message.text.strip()
    data = await state.get_data()
    q_id = data["q_id"]
    field = data["edit_field"]

    # ----- short_name -----
    if field == "short_name":
        if not raw:
            await message.answer("Короткое название не может быть пустым. Введи ещё раз.")
            return
        await update_question(conn, q_id, short_name=raw)
        await state.clear()
        await message.answer(f"✅ short_name обновлён для вопроса ID {q_id}.")
        return

    # ----- text -----
    if field == "text":
        if not raw:
            await message.answer("Текст вопроса не может быть пустым. Введи ещё раз.")
            return
        await update_question(conn, q_id, text=raw)
        await state.clear()
        await message.answer(f"✅ Текст вопроса обновлён для ID {q_id}.")
        return


    if field == "validation":
        if raw == "-" or raw == "":
            validation = None
        else:
            import json
            try:
                validation = json.loads(raw)
            except json.JSONDecodeError:
                await message.answer(
                    "Не смог распарсить JSON.\n\n"
                    f"{VALIDATION_HINT}"
                )
                return

        await update_question(conn, q_id, validation=validation)
        await state.clear()
        await message.answer(
            f"✅ Validation для вопроса ID {q_id} обновлён.\n"
        #     f"{'Правила очищены.' if validation is None else
        #     'Новые правила применены.'}"
        )
        return


    # ----- options -----
    if field == "options":
        if raw == "-":
            options = None
        else:
            options = [x.strip() for x in raw.split(",") if x.strip()]
            if not options:
                await message.answer(
                    "Не удалось выделить варианты. Введи варианты через запятую или '-' чтобы очистить."
                )
                return

        await update_question(conn, q_id, options=options)
        await state.clear()
        if options is None:
            await message.answer(f"✅ Варианты ответа очищены для вопроса ID {q_id}.")
        else:
            await message.answer(
                f"✅ Варианты ответа обновлены для вопроса ID {q_id}:\n" + ", ".join(options)
            )
        return

    # ----- validation -----
    if field == "validation":
        if raw == "-" or raw == "":
            validation = None
        else:
            import json
            try:
                validation = json.loads(raw)
            except json.JSONDecodeError:
                await message.answer(
                    "Не смог распарсить JSON.\n\n"
                    f"{VALIDATION_HINT}"
                )
                return

        await update_question(conn, q_id, validation=validation)
        await state.clear()
        await message.answer(
            f"✅ Validation для вопроса ID {q_id} обновлён.\n"
            f"{'Правила очищены.' if validation is None else 'Новые правила применены.'}"
        )
        return

    # На всякий случай fallback
    await message.answer("Неизвестное поле для редактирования. Попробуй ещё раз.")


@admin_router.callback_query(EditQuestion.edit_required, F.data.startswith("qreq:"))
async def edit_q_required(cb: CallbackQuery, state: FSMContext, conn: AsyncConnection):
    required_flag = cb.data.split(":", 1)[1] == "1"

    data = await state.get_data()
    q_id = data["q_id"]

    await update_question(conn, q_id, required=required_flag)

    await state.clear()
    await cb.message.edit_text(
        f"✅ Обязательность вопроса ID {q_id} изменена на: "
        f"{'обязательный' if required_flag else 'необязательный'}."
    )
    await cb.answer()




@admin_router.message(DeleteQuestion.wait_id)
async def delete_question_handle_id(message: Message, state: FSMContext, conn: AsyncConnection):
    raw = message.text.strip()

    # отмена
    if raw == "-" or raw.lower() in {"отмена", "cancel"}:
        await state.clear()
        await message.answer("Удаление отменено.")
        return

    if not raw.isdigit():
        await message.answer("Нужно ввести числовой ID вопроса или '-' для отмены.")
        return

    q_id = int(raw)

    # Проверяем, что вопрос существует
    row = await check_question(conn, q_id)
    if not row:
        await message.answer("Вопроса с таким ID не найдено. Введи другой ID или '-' для отмены.")
        return

    # Удаляем
    deleted = await delete_question(conn, q_id)
    if not deleted:
        await message.answer("Не удалось удалить вопрос (возможно, его уже удалили).")
        return

    await state.clear()
    await message.answer(
        f"✅ Вопрос удалён.\n"
        f"ID {row['id']} | #{row['sort_order']} | {row['short_name']}"
    )


@admin_router.message(F.text == LEXICON_RU['add_question'])
async def add_quest(message: Message, state: FSMContext):
    await state.set_state(EditAnswer.short_name)
    await message.answer(
        "Добавление нового вопроса.\n"
        "Введи короткое название вопроса.\n\n"
        "Например: ФИО, Телефон, Размер обуви."
        )

@admin_router.message(EditAnswer.short_name)
async def add_q_short_name(message: Message, state: FSMContext):
    short_name = message.text.strip()
    if not short_name:
        await message.answer("Короткое название не может быть пустым. Введи ещё раз.")
        return

    await state.update_data(short_name=short_name)
    await state.set_state(EditAnswer.text)
    await message.answer(
        "Теперь введи ПОЛНЫЙ текст вопроса, как его увидит пользователь.\n\n"
        "Например:\nВведите размер обуви\nНапример: 43"
    )

@admin_router.message(EditAnswer.text)
async def add_q_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Текст вопроса не может быть пустым. Введи ещё раз.")
        return

    await state.update_data(text=text)
    await state.set_state(EditAnswer.q_type)
    await message.answer("Выбери тип вопроса:", reply_markup=kb_q_types())

@admin_router.callback_query(EditAnswer.q_type, F.data.startswith("qtype:"))
async def add_q_type(cb: CallbackQuery, state: FSMContext):
    q_type = cb.data.split(":", 1)[1]   # text / number / date / phone / choice

    await state.update_data(q_type=q_type)
    await state.set_state(EditAnswer.required)
    await cb.message.edit_text("Этот вопрос должен быть обязательным?",
                               reply_markup=kb_required())
    await cb.answer()


async def add_q_validation(message: Message, state: FSMContext, conn: AsyncConnection):

    validation = None
    data = await state.get_data()
    short_name = data["short_name"]
    text = data["text"]
    q_type = data["q_type"]
    required = data["required"]
    options = data.get("options")

    form_id = await get_active_form(conn)

    new_id = await add_question(
        conn,
        form_id=form_id["id"],
        short_name=short_name,
        text=text,
        q_type=q_type,
        required=required,
        validation=validation,
        options=options,
    )

    # 5) Чистим состояние и говорим админу
    await state.clear()
    await message.answer(f"✅ Вопрос добавлен (id={new_id}).")

@admin_router.callback_query(EditAnswer.required, F.data.startswith("qreq:"))
async def add_q_required(cb: CallbackQuery, state: FSMContext, conn: AsyncConnection):
    required_flag = cb.data.split(":", 1)[1] == "1"
    await state.update_data(required=required_flag)
    data = await state.get_data()
    q_type = data["q_type"]

    if q_type == "choice":
        # нужно спросить варианты
        await state.set_state(EditAnswer.options)
        await cb.message.edit_text(
            "Введи варианты ответа через запятую.\n\n"
            "Например:\n 1, 2, 3, горячее, холодное"
        )
    else:
        # для остальных типов options не нужны, сразу спрашиваем validation
        await add_q_validation(cb.message, state, conn)
    await cb.answer()

@admin_router.message(EditAnswer.options)
async def add_q_options(message: Message, state: FSMContext, conn: AsyncConnection):
    raw = message.text.strip()
    if not raw:
        await message.answer("Нужно ввести хотя бы один вариант. Введи варианты через запятую.")
        return

    options = [x.strip() for x in raw.split(",") if x.strip()]
    if not options:
        await message.answer("Не получилось выделить варианты. Введи ещё раз через запятую.")
        return

    await state.update_data(options=options)
    await add_q_validation(message, state, conn)



