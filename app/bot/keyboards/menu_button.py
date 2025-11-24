from aiogram.types import BotCommand
from app.bot.enums.roles import UserRole


def get_main_menu_commands(LEXICON_RU: dict[str, str], role: UserRole):
    if role == UserRole.USER:
        return [
            BotCommand(
                command='/start',
                description=LEXICON_RU.get('/start_description')
            ),
            BotCommand(
                command='/fillform',
                description=LEXICON_RU.get('/fillform_description')
            ),
            BotCommand(
                command='/help',
                description=LEXICON_RU.get('/help_description')
            ),
        ]
    elif role == UserRole.ADMIN:
        return [
            BotCommand(
                command='/start',
                description=LEXICON_RU.get('/start_description')
            ),
            BotCommand(
                command='/fillform',
                description=LEXICON_RU.get('/fillform_description')
            ),
            BotCommand(
                command='/help',
                description=LEXICON_RU.get('/help_description')
            ),
            # BotCommand(
            #     command='/ban',
            #     description=LEXICON_RU.get('/ban_description')
            # ),
            # BotCommand(
            #     command='/unban',
            #     description=LEXICON_RU.get('/unban_description')
            # ),
            BotCommand(
                command='/statistics',
                description=LEXICON_RU.get('/statistics_description')
            ),
        ]