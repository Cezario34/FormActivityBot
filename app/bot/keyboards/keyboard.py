from aiogram.types import ReplyKeyboardMarkup,ReplyKeyboardRemove, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.bot.lexicon.lexicon import LEXICON_RU
from app.bot.enums.roles import UserRole
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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


def kb_q_types() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Текст", callback_data="qtype:text")],
        [InlineKeyboardButton(text="🔢 Число", callback_data="qtype:number")],
        [InlineKeyboardButton(text="📅 Дата", callback_data="qtype:date")],
        [InlineKeyboardButton(text="📱 Телефон", callback_data="qtype:phone")],
        [InlineKeyboardButton(text="✅ Выбор (кнопки)", callback_data="qtype:choice")],
    ])

def kb_required() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обязательный", callback_data="qreq:1")],
        [InlineKeyboardButton(text="Необязательный", callback_data="qreq:0")],
    ])

def kb_edit_fields() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название (short_name)", callback_data="eq:short_name")],
        [InlineKeyboardButton(text="Текст вопроса",        callback_data="eq:text")],
        [InlineKeyboardButton(text="Обязательность",       callback_data="eq:required")],
        [InlineKeyboardButton(text="Варианты (options)",   callback_data="eq:options")],
        [InlineKeyboardButton(text="Validation (JSON)",    callback_data="eq:validation")],
    ])