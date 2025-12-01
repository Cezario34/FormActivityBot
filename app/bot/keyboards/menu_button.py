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
            BotCommand(
                command='/edit_fill',
                description=LEXICON_RU.get('/editfill_description')
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
            BotCommand(
                command='/edit',
                description=LEXICON_RU.get('/edit_answer')
            ),
            BotCommand(
                command='/cancel_edit',
                description=LEXICON_RU.get('/cancel_edit_desc')
            ),
            BotCommand(
                command='/statistics',
                description=LEXICON_RU.get('/statistics_description')
            ),
        ]
    elif role == UserRole.DEVELOPER:
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
            BotCommand(
                command='/edit',
                description=LEXICON_RU.get('/edit_answer')
            ),
            BotCommand(
                command='/cancel_edit',
                description=LEXICON_RU.get('/cancel_edit_desc')
            ),
            BotCommand(
                command='/statistics',
                description=LEXICON_RU.get('/statistics_description')
            ),
            BotCommand(
                command='/change_role',
                description=LEXICON_RU.get('/add_admin_description')
                ),
        ]