# -*- coding: utf-8 -*-
"""
Тесты для форматтеров
"""
import unittest
from services.report.formatters import format_money, format_date, format_list, format_percent


class TestFormatters(unittest.TestCase):
    """Тесты для форматтеров"""
    
    def test_format_money(self):
        """Тест форматирования денег"""
        # Тест с None
        self.assertEqual(format_money(None), "—")
        
        # Тест с нулём
        self.assertEqual(format_money(0), "0,00 ₽")
        
        # Тест с положительным числом
        self.assertEqual(format_money(1234.5), "1 234,50 ₽")
        
        # Тест с большим числом
        self.assertEqual(format_money(1234567), "1 234 567,00 ₽")
        
        # Тест с отрицательным числом
        self.assertEqual(format_money(-1234.5), "-1 234,50 ₽")
    
    def test_format_date(self):
        """Тест форматирования дат"""
        # Тест с None
        self.assertEqual(format_date(None), "—")
        
        # Тест с правильной датой
        self.assertEqual(format_date("2023-12-31"), "31.12.2023")
        
        # Тест с неправильной датой
        self.assertEqual(format_date("invalid"), "invalid")
        
        # Тест с пустой строкой
        self.assertEqual(format_date(""), "")
    
    def test_format_list(self):
        """Тест форматирования списков"""
        # Тест с None
        self.assertEqual(format_list(None), "—")
        
        # Тест с пустым списком
        self.assertEqual(format_list([]), "—")
        
        # Тест с одним элементом
        self.assertEqual(format_list(["один"]), "один")
        
        # Тест с несколькими элементами
        self.assertEqual(format_list(["один", "два", "три"]), "один, два, три")
    
    def test_format_percent(self):
        """Тест форматирования процентов"""
        # Тест с None
        self.assertEqual(format_percent(None), "—")
        
        # Тест с нулём
        self.assertEqual(format_percent(0), "0,00 %")
        
        # Тест с положительным числом
        self.assertEqual(format_percent(12.34), "12,34 %")
        
        # Тест с отрицательным числом
        self.assertEqual(format_percent(-5.67), "-5,67 %")


if __name__ == '__main__':
    unittest.main()