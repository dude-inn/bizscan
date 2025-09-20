# -*- coding: utf-8 -*-
"""
Тесты для formatters.py
"""
import pytest
from services.report.formatters import format_money, format_date, format_list, format_percent


class TestFormatters:
    """Тесты для функций форматирования"""
    
    def test_format_money_none(self):
        """Тест форматирования None"""
        result = format_money(None)
        assert result == "—"
    
    def test_format_money_zero(self):
        """Тест форматирования нуля"""
        result = format_money(0)
        assert result == "0,00 ₽"
    
    def test_format_money_positive(self):
        """Тест форматирования положительных чисел"""
        result = format_money(101000.65)
        assert result == "101 000,65 ₽"
    
    def test_format_money_large_number(self):
        """Тест форматирования больших чисел"""
        result = format_money(1234567)
        assert result == "1 234 567,00 ₽"
    
    def test_format_money_decimal(self):
        """Тест форматирования десятичных чисел"""
        result = format_money(12.3)
        assert result == "12,30 ₽"
    
    def test_format_money_negative(self):
        """Тест форматирования отрицательных чисел"""
        result = format_money(-50000.25)
        assert result == "-50 000,25 ₽"
    
    def test_format_money_string(self):
        """Тест форматирования строки"""
        result = format_money("1234.56")
        assert result == "1 234,56 ₽"
    
    def test_format_money_string_with_commas(self):
        """Тест форматирования строки с запятыми"""
        result = format_money("1,234.56")
        assert result == "1 234,56 ₽"
    
    def test_format_money_invalid_string(self):
        """Тест форматирования невалидной строки"""
        result = format_money("invalid")
        assert result == "—"
    
    def test_format_date_none(self):
        """Тест форматирования None"""
        result = format_date(None)
        assert result == "—"
    
    def test_format_date_iso_format(self):
        """Тест форматирования ISO даты"""
        result = format_date("2023-03-15")
        assert result == "15.03.2023"
    
    def test_format_date_iso_format_with_time(self):
        """Тест форматирования ISO даты с временем"""
        result = format_date("2023-03-15T10:30:00")
        assert result == "2023-03-15T10:30:00"  # Возвращается как есть
    
    def test_format_date_already_formatted(self):
        """Тест форматирования уже отформатированной даты"""
        result = format_date("15.03.2023")
        assert result == "15.03.2023"
    
    def test_format_date_invalid_format(self):
        """Тест форматирования невалидной даты"""
        result = format_date("invalid-date")
        assert result == "—"
    
    def test_format_list_none(self):
        """Тест форматирования None"""
        result = format_list(None)
        assert result == "—"
    
    def test_format_list_empty(self):
        """Тест форматирования пустого списка"""
        result = format_list([])
        assert result == "—"
    
    def test_format_list_strings(self):
        """Тест форматирования списка строк"""
        result = format_list(["НДС", "Налог на прибыль", "Налог на имущество"])
        assert result == "НДС, Налог на прибыль, Налог на имущество"
    
    def test_format_list_mixed_types(self):
        """Тест форматирования списка смешанных типов"""
        result = format_list(["НДС", 100000, "Налог на прибыль"])
        assert result == "НДС, 100000, Налог на прибыль"
    
    def test_format_list_single_item(self):
        """Тест форматирования списка с одним элементом"""
        result = format_list(["НДС"])
        assert result == "НДС"
    
    def test_format_percent_none(self):
        """Тест форматирования None"""
        result = format_percent(None)
        assert result == "—"
    
    def test_format_percent_integer(self):
        """Тест форматирования целого числа"""
        result = format_percent(15)
        assert result == "15.00 %"
    
    def test_format_percent_float(self):
        """Тест форматирования числа с плавающей точкой"""
        result = format_percent(15.5)
        assert result == "15.50 %"
    
    def test_format_percent_string(self):
        """Тест форматирования строки"""
        result = format_percent("15.5")
        assert result == "15.50 %"
    
    def test_format_percent_string_with_percent(self):
        """Тест форматирования строки с символом %"""
        result = format_percent("15.5%")
        assert result == "15.50 %"
    
    def test_format_percent_string_with_comma(self):
        """Тест форматирования строки с запятой"""
        result = format_percent("15,5")
        assert result == "15.50 %"
    
    def test_format_percent_negative(self):
        """Тест форматирования отрицательного числа"""
        result = format_percent(-5.25)
        assert result == "-5.25 %"
    
    def test_format_percent_zero(self):
        """Тест форматирования нуля"""
        result = format_percent(0)
        assert result == "0.00 %"
    
    def test_format_percent_invalid_string(self):
        """Тест форматирования невалидной строки"""
        result = format_percent("invalid")
        assert result == "—"
    
    def test_format_money_edge_cases(self):
        """Тест граничных случаев для format_money"""
        # Очень маленькое число
        result = format_money(0.01)
        assert result == "0,01 ₽"
        
        # Очень большое число
        result = format_money(999999999.99)
        assert result == "999 999 999,99 ₽"
        
        # Число с многими знаками после запятой
        result = format_money(123.456789)
        assert result == "123,46 ₽"  # Округляется до 2 знаков
    
    def test_format_date_edge_cases(self):
        """Тест граничных случаев для format_date"""
        # Дата в начале года
        result = format_date("2023-01-01")
        assert result == "01.01.2023"
        
        # Дата в конце года
        result = format_date("2023-12-31")
        assert result == "31.12.2023"
        
        # Високосный год
        result = format_date("2024-02-29")
        assert result == "29.02.2024"
    
    def test_format_list_edge_cases(self):
        """Тест граничных случаев для format_list"""
        # Список с пустыми строками
        result = format_list(["", "НДС", ""])
        assert result == ", НДС, "
        
        # Список с None
        result = format_list([None, "НДС", None])
        assert result == "None, НДС, None"
        
        # Список с очень длинными строками
        long_string = "Очень длинная строка " * 10
        result = format_list([long_string, "НДС"])
        assert result == f"{long_string}, НДС"
