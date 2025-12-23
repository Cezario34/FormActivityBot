from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.kbd import Start, Row, Button

from app.bot.getter.admins import delq_confirm_getter, delq_list_getter
from app.bot.handlers.admin import delq_on_id_input
from app.bot.keyboards.edit_menu import delq_confirm_yes, delq_confirm_no
from app.bot.states.admin import AdminEditQuestionSG, AdminDeleteQuestionSG

delete_question_dialog  = Dialog(
    Window(
        Format("{text}"),
        MessageInput(delq_on_id_input),
        getter=delq_list_getter,
        state=AdminDeleteQuestionSG.show_questions
    ),
    Window(
        Format("{confirm_text}"),
        Row(
            Button(Const("✅ Да, удалить"), id="del_yes", on_click=delq_confirm_yes),
            Button(Const("↩️ Нет"), id="del_no", on_click=delq_confirm_no),
        ),
        getter = delq_confirm_getter,
        state = AdminDeleteQuestionSG.confirm,
    ))
