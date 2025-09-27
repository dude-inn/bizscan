# -*- coding: utf-8 -*-
"""
Тесты для новой архитектуры отчётов
"""
import unittest
from unittest.mock import Mock, patch
import asyncio
from services.report.builder import ReportBuilder
from services.report.formatters import format_money, format_date, format_list, format_percent
from services.report.flattener import flatten, apply_aliases, pick
from services.aggregator import fetch_company_report_markdown
import services.aggregator as aggregator


class TestNewReportBuilder(unittest.TestCase):
    """Тесты для нового ReportBuilder"""
    
    def setUp(self):
        """Настройка тестов"""
        self.builder = ReportBuilder()
    
    @patch('services.report.builder.OFDataClient')
    def test_build_simple_report_success(self, mock_client_class):
        """Тест успешного построения отчёта"""
        # Мокаем клиент
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Мокаем данные компании
        mock_company_data = {
            'data': {
                'НаимПолн': 'ООО "ТЕСТ"',
                'ИНН': '1234567890',
                'ОГРН': '1234567890123',
                'ДатаРег': '2020-01-01',
                'Регион': {'Наим': 'Москва'},
                'Налоги': {
                    'СведУплГод': '2023',
                    'СумУпл': 100000,
                    'СведУпл': [
                        {'Наим': 'НДС', 'Сумма': 50000},
                        {'Наим': 'Налог на прибыль', 'Сумма': 30000}
                    ]
                }
            }
        }
        mock_client.get_company.return_value = mock_company_data
        
        # Создаём новый builder с моком
        builder = ReportBuilder()
        builder.client = mock_client
        
        # Тестируем
        result = builder.build_simple_report(
            ident={'inn': '1234567890'},
            include=['company', 'taxes']
        )
        
        self.assertIsInstance(result, str)
        self.assertIn('ООО "ТЕСТ"', result)
        self.assertIn('НАЛОГИ', result)
        self.assertIn('НДС', result)
    
    @patch('services.report.builder.OFDataClient')
    def test_build_simple_report_company_not_found(self, mock_client_class):
        """Тест случая, когда компания не найдена"""
        # Мокаем клиент
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_company.return_value = None
        
        # Создаём новый builder с моком
        builder = ReportBuilder()
        builder.client = mock_client
        
        # Тестируем
        result = builder.build_simple_report(
            ident={'inn': '1234567890'},
            include=['company']
        )
        
        self.assertIn('❌ Компания не найдена', result)
    
    def test_summarize_history_and_bullets(self):
        """Тест генерации истории и резюме"""
        test_text = """
        ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ТЕСТ"
        ИНН 1234567890 • ОГРН 1234567890123 • Дата регистрации 01.01.2020
        
        ОСНОВНОЕ
        ==================================================
        ИНН: 1234567890
        Регион: Москва
        """
        
        history, bullets = self.builder.summarize_history_and_bullets(test_text)
        
        self.assertIsInstance(history, str)
        self.assertIsInstance(bullets, str)
        self.assertIn("ТЕСТ", history)
        self.assertIn("•", bullets)


class TestFormatters(unittest.TestCase):
    """Тесты для форматтеров"""
    
    def test_format_money(self):
        """Тест форматирования денег"""
        # Тест с None
        self.assertEqual(format_money(None), "—")
        
        # Тест с нулём
        self.assertEqual(format_money(0), "0,00 ₽")
        
        # Тест с положительным числом
        result = format_money(1234.5)
        self.assertIn("1", result)
        self.assertIn("234", result)
        self.assertIn("₽", result)
    
    def test_format_date(self):
        """Тест форматирования дат"""
        # Тест с None
        self.assertEqual(format_date(None), "—")
        
        # Тест с правильной датой
        self.assertEqual(format_date("2023-12-31"), "31.12.2023")
        
        # Тест с неправильной датой
        self.assertEqual(format_date("invalid"), "invalid")
    
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
        result = format_percent(0)
        self.assertIn("0", result)
        self.assertIn("%", result)


class TestFlattener(unittest.TestCase):
    """Тесты для flattener"""
    
    def test_flatten_simple_dict(self):
        """Тест flatten для простого словаря"""
        data = {"a": 1, "b": {"c": 2}}
        result = flatten(data)
        
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b.c"], 2)
    
    def test_flatten_with_arrays(self):
        """Тест flatten для словаря с массивами"""
        data = {"items": [{"name": "test1"}, {"name": "test2"}]}
        result = flatten(data)
        
        self.assertEqual(result["items[0].name"], "test1")
        self.assertEqual(result["items[1].name"], "test2")
    
    def test_apply_aliases(self):
        """Тест применения алиасов"""
        flat_data = {"a": 1, "b": 2}
        aliases = {"a": "Алиас A", "b": "Алиас B"}
        result = apply_aliases(flat_data, aliases)
        
        self.assertEqual(result["Алиас A"], 1)
        self.assertEqual(result["Алиас B"], 2)
    
    def test_pick(self):
        """Тест pick для выбора подмножества"""
        flat_data = {"a": 1, "a.b": 2, "b": 3}
        result = pick(flat_data, "a")
        
        self.assertEqual(result[""], 1)  # "a" становится ""
        self.assertEqual(result["b"], 2)  # "a.b" становится "b"
        self.assertEqual(len(result), 2)  # Только 2 элемента в результате


class TestAggregator(unittest.TestCase):
    """Тесты для агрегатора"""

    def setUp(self):
        aggregator._builder = None
    
    @patch('services.aggregator.ReportBuilder')
    def test_fetch_company_report_markdown_inn(self, mock_builder_class):
        """Тест получения отчёта по ИНН"""
        # Мокаем builder
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder
        mock_builder.build_simple_report.return_value = "Тестовый отчёт"
        
        # Тестируем
        result = asyncio.run(fetch_company_report_markdown("1234567890"))
        
        self.assertEqual(result, "Тестовый отчёт")
        mock_builder.build_simple_report.assert_called_once()
    
    @patch('services.aggregator._builder', None)
    @patch('services.aggregator.ReportBuilder')
    def test_fetch_company_report_markdown_name(self, mock_builder_class):
        """Тест получения отчёта по названию"""
        # Мокаем builder
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder
        mock_builder.build_simple_report.return_value = "Тестовый отчёт"
        
        # Тестируем
        result = asyncio.run(fetch_company_report_markdown("ООО ТЕСТ"))
        
        self.assertEqual(result, "Тестовый отчёт")
        mock_builder.build_simple_report.assert_called_once()


if __name__ == '__main__':
    unittest.main()



