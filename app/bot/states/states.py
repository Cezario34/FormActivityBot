from aiogram.fsm.state import StatesGroup, State

class FormFilling(StatesGroup):
    answer = State()

class MenuEdit(StatesGroup):
    edit_quest = State()



class EditAnswer(StatesGroup):
    short_name = State()
    text = State()
    q_type = State()
    required = State()
    options = State()
    validation = State()


class DeleteQuestion(StatesGroup):
    wait_id = State()

class EditQuestion(StatesGroup):
    wait_id = State()
    choose_field = State()
    edit_value = State()
    edit_required = State()
