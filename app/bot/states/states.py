from aiogram.fsm.state import StatesGroup, State

class FormFilling(StatesGroup):
    answer = State()


class EditAnswer(StatesGroup):
    edit_answer = State()