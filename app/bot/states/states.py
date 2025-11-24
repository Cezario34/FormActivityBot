from aiogram.fsm.state import StatesGroup, State

class FormFilling(StatesGroup):
    answer = State()