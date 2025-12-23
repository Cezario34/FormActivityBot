from aiogram.fsm.state import State, StatesGroup


class AdminEditQuestionSG(StatesGroup):
    show_questions = State()
    wait_id = State()

class AdminAddQuestionSG(StatesGroup):
    add_q = State()

class AdminDeleteQuestionSG(StatesGroup):
    show_questions = State()
    confirm = State()

class AdminSwitchQuestionSG(StatesGroup):
    show_question = State()
    wait_pair = State()