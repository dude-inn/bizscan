# -*- coding: utf-8 -*-
"""
Актуальные тесты для агрегатора текстового отчёта
"""
import asyncio
from unittest.mock import Mock, patch

from services import aggregator
from services.aggregator import build_markdown_report


class TestReportRenderer:
    """Проверяет вспомогательную функцию build_markdown_report"""

    def setup_method(self):
        aggregator._builder = None

    def test_build_markdown_report_success(self):
        profile = {"company": {"ИНН": "1234567890"}}

        with patch("services.aggregator.ReportBuilder") as mock_builder_class:
            mock_builder = Mock()
            mock_builder.build_simple_report.return_value = "Отчёт"
            mock_builder_class.return_value = mock_builder

            result = asyncio.run(build_markdown_report(profile))

            assert result == "Отчёт"
            mock_builder.build_simple_report.assert_called_once_with(
                ident={"inn": "1234567890"},
                include=[
                    "company",
                    "taxes",
                    "finances",
                    "legal-cases",
                    "enforcements",
                    "inspections",
                    "contracts",
                ],
            )

    def test_builder_reuse_between_calls(self):
        profile = {"company": {"ИНН": "1234567890"}}

        with patch("services.aggregator.ReportBuilder") as mock_builder_class:
            mock_builder = Mock()
            mock_builder.build_simple_report.return_value = "Первый"
            mock_builder_class.return_value = mock_builder

            first = asyncio.run(build_markdown_report(profile))
            mock_builder.build_simple_report.return_value = "Второй"
            second = asyncio.run(build_markdown_report(profile))

            assert first == "Первый"
            assert second == "Второй"
            assert mock_builder.build_simple_report.call_count == 2
            mock_builder_class.assert_called_once()

    def test_build_markdown_report_missing_inn(self):
        profile = {"company": {"Название": "Без ИНН"}}

        result = asyncio.run(build_markdown_report(profile))

        assert result.startswith("❌ ИНН не найден")

