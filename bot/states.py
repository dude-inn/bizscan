# -*- coding: utf-8 -*-
from aiogram.fsm.state import StatesGroup, State

class MenuState(StatesGroup):
    MAIN = State()
    REPORT_MENU = State()

class SearchState(StatesGroup):
    ASK_INN = State()
    ASK_NAME = State()
    PAGING = State()
    SELECT = State()

class ReportState(StatesGroup):
    CHOOSE = State()
    GENERATE = State()

