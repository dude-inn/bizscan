# -*- coding: utf-8 -*-
"""
Тесты для ReportBuilder
"""
import unittest
from unittest.mock import Mock, patch
from services.report.builder import ReportBuilder


class TestReportBuilder(unittest.TestCase):
    """Тесты для ReportBuilder"""
    
    def setUp(self):
        """Настройка тестов"""
        self.builder = ReportBuilder()
    
    def test_init(self):
        """Тест инициализации"""
        self.assertIsNotNone(self.builder.client)
        self.assertIsNone(self.builder.openai_client)
    
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
                    'СумУпл': 100000
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


if __name__ == '__main__':
    unittest.main()

