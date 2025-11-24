from app.bot.enums.roles import UserRole

BASE_KB = {
    "/start": "Перезапустить бота",
    "/help": "Справка",
    "/fillform": "Заполнить анкету",
    "/cancel": "Отменить заполнение"
}

ADMIN_EXTRA_KB = {
    "/statistic": "Статистика",
    "/edit": "Редактировать анкету",
}

def build_kb(role: UserRole) -> dict[str, str]:
    if role == UserRole.ADMIN:
        return {**BASE_KB, **ADMIN_EXTRA_KB}   # или BASE_KB | ADMIN_EXTRA_KB
    return BASE_KB