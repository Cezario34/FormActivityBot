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


class EditFillform(StatesGroup):
    choise_question = State()
    new_answer = State()


class SwitchQuestion(StatesGroup):
    wait_two_quest= State()


class SwtitchRole(StatesGroup):
    editrole = State()
    wait_role = State()