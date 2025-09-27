# -*- coding: utf-8 -*-
"""
Тесты для агрегатора
"""
import unittest
from unittest.mock import patch, Mock
import asyncio
import services.aggregator as aggregator
from services.aggregator import fetch_company_report_markdown, fetch_company_profile


async def _immediate_asyncio_to_thread(func, /, *args, **kwargs):
    return func(*args, **kwargs)


class TestAggregator(unittest.TestCase):
    """Тесты для агрегатора"""
    
    def setUp(self):
        """Настройка тестов"""
        aggregator._builder = None
        self.test_inn = "1234567890"
        self.test_ogrn = "1234567890123"
        self.test_name = "ООО ТЕСТ"
    
    @patch('services.aggregator.asyncio_to_thread', new=_immediate_asyncio_to_thread)
    @patch('services.aggregator.ReportBuilder')
    def test_fetch_company_report_markdown_inn(self, mock_builder_class):
        """Тест получения отчёта по ИНН"""
        # Мокаем builder
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder
        mock_builder.build_simple_report.return_value = "Тестовый отчёт"
        
        # Тестируем
        result = asyncio.run(fetch_company_report_markdown(self.test_inn))
        
        self.assertEqual(result, "Тестовый отчёт")
        mock_builder.build_simple_report.assert_called_once_with(
            ident={'inn': self.test_inn},
            include=['company', 'taxes', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts'],
            max_rows=500
        )
    
    @patch('services.aggregator.asyncio_to_thread', new=_immediate_asyncio_to_thread)
    @patch('services.aggregator.ReportBuilder')
    def test_fetch_company_report_markdown_ogrn(self, mock_builder_class):
        """Тест получения отчёта по ОГРН"""
        # Мокаем builder
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder
        mock_builder.build_simple_report.return_value = "Тестовый отчёт"
        
        # Тестируем
        result = asyncio.run(fetch_company_report_markdown(self.test_ogrn))
        
        self.assertEqual(result, "Тестовый отчёт")
        mock_builder.build_simple_report.assert_called_once_with(
            ident={'ogrn': self.test_ogrn},
            include=['company', 'taxes', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts'],
            max_rows=500
        )
    
    @patch('services.aggregator.asyncio_to_thread', new=_immediate_asyncio_to_thread)
    @patch('services.aggregator.ReportBuilder')
    def test_fetch_company_report_markdown_name(self, mock_builder_class):
        """Тест получения отчёта по названию"""
        # Мокаем builder
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder
        mock_builder.build_simple_report.return_value = "Тестовый отчёт"
        
        # Тестируем
        result = asyncio.run(fetch_company_report_markdown(self.test_name))
        
        self.assertEqual(result, "Тестовый отчёт")
        mock_builder.build_simple_report.assert_called_once_with(
            ident={'name': self.test_name},
            include=['company', 'taxes', 'finances', 'legal-cases', 'enforcements', 'inspections', 'contracts'],
            max_rows=500
        )
    
    @patch('services.aggregator.asyncio_to_thread', new=_immediate_asyncio_to_thread)
    @patch('services.aggregator.ReportBuilder')
    def test_fetch_company_profile(self, mock_builder_class):
        """Тест получения профиля компании"""
        # Мокаем builder
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder
        mock_builder.build_company_profile.return_value = {"company": "data"}
        
        # Тестируем
        result = asyncio.run(fetch_company_profile(self.test_inn))
        
        self.assertEqual(result, {"company": "data"})
        mock_builder.build_company_profile.assert_called_once_with(self.test_inn)


if __name__ == '__main__':
    unittest.main()








