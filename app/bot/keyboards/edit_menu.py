from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from app.bot.states.admin import AdminDeleteQuestionSG
from app.infrastructure.database.edit_answer_db import delete_question


async def delq_confirm_yes(cb: CallbackQuery, widget, dialog_manager: DialogManager, **kwargs):
    conn = dialog_manager.middleware_data["conn"]
    q_id = dialog_manager.dialog_data.get("q_id")

    if q_id is None:
        await cb.answer("Нет выбранного вопроса", show_alert=True)
        return

    deleted = await delete_question(conn, q_id)
    if not deleted:
        await cb.answer("Не удалось удалить (возможно уже удалён)", show_alert=True)
        # вернёмся к списку
        await dialog_manager.switch_to(AdminDeleteQuestionSG.show_questions)
        return

    await cb.answer("Удалено")
    # после удаления возвращаемся к списку (можно и done(), если хочешь закрывать диалог)
    await dialog_manager.switch_to(AdminDeleteQuestionSG.show_questions)

async def delq_confirm_no(cb: CallbackQuery, widget, dialog_manager: DialogManager):
    await cb.answer("Отмена")
    await dialog_manager.switch_to(AdminDeleteQuestionSG.show_questions)