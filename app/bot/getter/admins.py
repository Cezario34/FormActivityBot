from aiogram_dialog import DialogManager

from app.infrastructure.database.db import get_active_form
from app.infrastructure.database.edit_answer_db import get_active_questions, \
    check_question
from aiogram_dialog import DialogManager

async def delq_list_getter(dialog_manager: DialogManager, **kwargs):
    conn = dialog_manager.middleware_data["conn"]
    form = await get_active_form(conn)
    if not form:
        return {
            "text":"Нет активной формы. Сначала создайте/активируйте анкету.",
            "has_questions": False,
            }

    questions = await get_active_questions(conn, form["id"])
    if not questions:
        return {
            "text": "В активной анкете нет вопросов.",
            "has_questions": False,
        }

    lines = ["Текущие вопросы анкеты:\n"]
    for q in questions:
        rid = q["id"]
        order = q["sort_order"]
        sn = q["short_name"]
        qt = q["q_type"]
        req = "обязат." if q["required"] else "необязат."
        lines.append(f"ID {order+1} | {sn} ({qt}, {req})")

    lines.append("\nОтправь номер вопроса (например:3). ")
    return {
        "text": "\n".join(lines),
        "has_questions": True
        }

async def delq_confirm_getter(dialog_manager: DialogManager, **kwargs):
    conn = dialog_manager.middleware_data["conn"]
    q_id = dialog_manager.dialog_data.get("q_id")

    if q_id is None:
        return {"confirm_text" : "Не выбран вопрос для удлаения"}

    q = await check_question(conn, q_id)
    if not q:
        return {"confirm_text": "Вопрос уже не найден. Вернись к списку."}

    return {
        "confirm_text": (
            "Удалить вопрос?\n\n"
            f"{q['sort_order']+1}. {q['short_name']}\n\n"
            "Подтверди действие."
        )
    }