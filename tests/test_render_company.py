# -*- coding: utf-8 -*-
"""
Актуальные тесты для render_company.py
"""
from services.report.render_company import render_company


class TestRenderCompany:
    """Проверяет текстовый рендер компании с новым форматом"""

    def test_render_company_with_taxes(self):
        data = {
            "НаимПолн": "ООО Тестовая компания",
            "ИНН": "1234567890",
            "ОГРН": "1234567890123",
            "ДатаРег": "2020-03-15",
            "Адрес": {"АдресРФ": "г. Москва, ул. Тестовая, д. 1"},
            "Контакты": {
                "Тел": ["+7-495-123-45-67", "+7-495-123-45-68"],
                "Емэйл": ["test@example.com", "info@example.com"],
                "ВебСайт": "https://example.com",
            },
            "Налоги": {
                "ОсобРежим": ["УСН", "ПСН"],
                "СведУплГод": "2023",
                "СумУпл": 1500000,
                "СведУпл": [
                    {"Наим": "НДС", "Сумма": 800000},
                    {"Наим": "Налог на прибыль", "Сумма": 500000},
                ],
                "СумНедоим": 50000,
                "НедоимДата": "2023-12-31",
            },
            "Учредители": [
                {"Наим": "Иванов Иван Иванович", "ДоляПроц": "60"},
                {"Наим": "Петров Петр Петрович", "ДоляПроц": "40"},
            ],
        }

        result = render_company(data)

        assert "НАЗВАНИЕ: ООО Тестовая компания" in result
        assert "ИНН: 1234567890" in result
        assert "Адрес:" in result
        assert "Налоги:" in result
        assert "ОсобРежим:" in result
        assert "1. УСН" in result
        assert "СведУплГод: 2023" in result
        assert "СумУпл: 1500000" in result
        assert "1. Наименование: НДС | Сумма: 800 000,00 ₽" in result
        assert "СумНедоим: 50000" in result
        assert "НедоимДата: 31.12.2023" in result
        assert "Учредители:" in result
        assert "1. Наименование: Иванов Иван Иванович | ДоляПроц: 60,00 %" in result

    def test_render_company_without_taxes(self):
        data = {
            "НаимПолн": "ООО Простая компания",
            "ИНН": "9876543210",
            "ОГРН": "9876543210987",
            "ДатаРег": "2021-06-01",
            "Адрес": {"АдресРФ": "г. Санкт-Петербург, ул. Простая, д. 2"},
            "Контакты": {
                "Тел": ["+7-812-987-65-43"],
                "Емэйл": ["simple@example.com"],
            },
            "Учредители": [
                {"Наим": "Сидоров Сидор Сидорович", "ДоляПроц": "100"},
            ],
        }

        result = render_company(data)

        assert "НАЗВАНИЕ: ООО Простая компания" in result
        assert "Контакты:" in result
        assert "Телефоны:" in result
        assert "+7-812-987-65-43" in result
        assert "Email:" in result
        assert "simple@example.com" in result
        assert "Учредители:" in result
        assert "ДоляПроц: 100,00 %" in result
        assert "Налоги:" not in result

    def test_render_company_empty_fields(self):
        data = {
            "НаимПолн": "ООО Пустая компания",
            "ИНН": "1111111111",
            "ОГРН": "1111111111111",
            "ДатаРег": "2019-05-20",
            "ОКВЭДОсн": {},
            "Контакты": {"Тел": [], "Емэйл": []},
            "Налоги": {},
            "Учредители": [],
        }

        result = render_company(data)

        assert "ОКВЭДОсн: отсутствуют" in result
        assert "Контакты:" in result
        assert "Телефоны: отсутствуют" in result
        assert "Email: отсутствуют" in result
        assert "Налоги: отсутствуют" in result
        assert "Учредители: отсутствуют" in result

    def test_render_company_missing_fields(self):
        data = {
            "НаимПолн": "ООО Неполная компания",
            "ИНН": "2222222222",
        }

        result = render_company(data)

        assert "НАЗВАНИЕ: ООО Неполная компания" in result
        assert "ИНН: 2222222222" in result
        assert "ОГРН: не указано" in result
        assert "ДАТА РЕГИСТРАЦИИ: не указано" in result

    def test_render_company_partial_taxes(self):
        data = {
            "НаимПолн": "ООО Частичная компания",
            "ИНН": "3333333333",
            "ОГРН": "3333333333333",
            "ДатаРег": "2023-01-01",
            "Налоги": {
                "ОсобРежим": ["УСН"],
                "СведУплГод": "2023",
                "СумУпл": 500000,
                "СведУпл": [
                    {"Наим": "НДС", "Сумма": 300000},
                    {"Наим": "Налог на прибыль", "Сумма": 200000},
                ],
            },
            "Учредители": [
                {"Наим": "Тестов Тест Тестович", "ДоляПроц": "100"},
            ],
        }

        result = render_company(data)

        assert "Налоги:" in result
        assert "ОсобРежим:" in result
        assert "СумУпл: 500000" in result
        assert "1. Наименование: НДС | Сумма: 300 000,00 ₽" in result
        assert "2. Наименование: Налог на прибыль | Сумма: 200 000,00 ₽" in result
        assert "СумНедоим" not in result
        assert "Учредители:" in result
        assert "Тестов Тест Тестович" in result

    def test_render_company_many_founders(self):
        data = {
            "НаимПолн": "ООО МногоУчредителей",
            "ИНН": "4444444444",
            "ОГРН": "4444444444444",
            "ДатаРег": "2023-01-01",
            "Учредители": [
                {"Наим": f"Учредитель {i}", "ДоляПроц": 6}
                for i in range(15)
            ],
        }

        result = render_company(data)

        assert "Учредители:" in result
        assert "1. Наименование: Учредитель 0 | ДоляПроц: 6,00 %" in result
        assert "15. Наименование: Учредитель 14 | ДоляПроц: 6,00 %" in result

    def test_render_company_txt_format(self):
        data = {
            "НаимПолн": "ООО TXT Компания",
            "ИНН": "5555555555",
            "ОГРН": "5555555555555",
            "ДатаРег": "2023-01-01",
        }

        result = render_company(data)

        assert "<" not in result
        assert ">" not in result
        assert "**" not in result
        assert "__" not in result
        assert "##" not in result
        assert "НАЗВАНИЕ:" in result
        assert "ИНН:" in result
        assert "ОГРН:" in result
        assert "ДАТА РЕГИСТРАЦИИ:" in result
