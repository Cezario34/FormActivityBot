from app.bot.states.users import StartDialogSG
from app.bot.getter.user import start_getter
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.kbd import Start, Row

start_dialog = Dialog(
    Window(
        Format("{start_text}"),

    getter = start_getter,
    state = StartDialogSG.start
    )
)