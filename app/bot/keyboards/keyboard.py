from aiogram.types import ReplyKeyboardMarkup,ReplyKeyboardRemove, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.bot.lexicon.lexicon import LEXICON_RU
from app.bot.enums.roles import UserRole

# Функция для формирования инлайн-клавиатуры на лету
def create_kb(lexicon_kb: dict[str, str], width: int = 2):
    kb_builder = ReplyKeyboardBuilder()
    buttons = [KeyboardButton(text=t) for t in lexicon_kb.values()]
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup(resize_keyboard=True)


def keyboard_answer(q: dict, width: int = 2) -> ReplyKeyboardMarkup | None:
    if q["q_type"] != "choice" or not q.get("options"):
        return ReplyKeyboardRemove()

    buttons = [[KeyboardButton(text=opt)] for opt in q["options"]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

