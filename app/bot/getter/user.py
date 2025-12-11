from aiogram_dialog import DialogManager

from app.bot.keyboards.info_kb import build_kb


async def start_getter(dialog_manager: DialogManager,**kwargs):


    LEXICON_RU = kwargs["LEXICON_RU"]

    start_data = dialog_manager.start_data or {}
    user_role = start_data.get('user_role')
    lexicon_kb = build_kb(user_role)

    return {
        "start_text": LEXICON_RU.get("/start"),
        "lexicon_kb": lexicon_kb,
        "user_role": user_role,
    }