# -*- coding: utf-8 -*-
"""
Константы для модуля отчётов
"""

# Размеры данных
DEFAULT_MAX_ROWS = 100
DEFAULT_TOP_TAXES = 5
DEFAULT_TOP_FINANCES = 10
DEFAULT_TOP_LEGAL = 10
DEFAULT_TOP_ENFORCE = 10
DEFAULT_TOP_INSPECT = 10
DEFAULT_TOP_CONTRACTS = 10

# Секции отчёта
SECTION_HEADERS = {
    'company': 'ОСНОВНОЕ',
    'taxes': 'НАЛОГИ', 
    'finances': 'ФИНАНСОВАЯ ОТЧЁТНОСТЬ',
    'legal-cases': 'АРБИТРАЖНЫЕ ДЕЛА',
    'enforcements': 'ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА',
    'inspections': 'ПРОВЕРКИ',
    'contracts': 'ГОСЗАКУПКИ',
    'entrepreneur': 'ИП'
}

# OpenAI секции отключены
OPENAI_SECTIONS = {}

# Сообщения об ошибках
ERROR_MESSAGES = {
    'company_not_found': '❌ Компания не найдена или некорректный ИНН/ОГРН',
    'data_unavailable': 'Данные недоступны',
    'report_error': '❌ Ошибка при формировании отчёта: {error}',
    'api_error': '❌ Ошибка API: {error}'
}

# Форматирование
SECTION_SEPARATOR = '=' * 50
BULLET_POINT = '• '
EMPTY_FIELD = '—'

# Финансовые коды
FINANCE_CODES = {
    '2110': 'Выручка',
    '2400': 'Чистая прибыль/убыток',
    '3200': 'Капитал и резервы'
}

# Налоговые режимы
TAX_REGIMES = {
    'УСН': 'Упрощённая система налогообложения',
    'ОСН': 'Общая система налогообложения',
    'ЕНВД': 'Единый налог на вменённый доход',
    'ПСН': 'Патентная система налогообложения'
}



