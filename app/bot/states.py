from aiogram.fsm.state import State, StatesGroup


class UnlockFlow(StatesGroup):
    waiting_for_pin = State()
