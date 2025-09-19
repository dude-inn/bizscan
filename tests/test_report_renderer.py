# -*- coding: utf-8 -*-
"""
Tests for report rendering functions
"""
import pytest
from decimal import Decimal
from services.aggregator import build_markdown_report
from services.mappers.datanewton import CompanyCard, FinanceSnapshot, ArbitrationCase, ArbitrationSummary


class TestReportRenderer:
    """Test report rendering functionality"""
    
    def test_render_with_complete_data(self):
        """Test report rendering with complete data"""
        card = CompanyCard(
            inn="1234567890",
            ogrn="1234567890123",
            kpp="123456789",
            name_full="Test Company LLC",
            name_short="Test LLC",
            registration_date="2020-01-01",
            status_code="ACTIVE",
            status_text="Действует",
            address="123 Test Street, Test City",
            manager_name="John Doe",
            manager_post="CEO",
            okved="62.01",
            is_msme=True
        )
        
        finances = [
            FinanceSnapshot(
                period="2023",
                revenue=Decimal("1000000"),
                net_profit=Decimal("100000"),
                assets=Decimal("500000"),
                equity=Decimal("300000"),
                long_term_liabilities=Decimal("100000"),
                short_term_liabilities=Decimal("100000")
            )
        ]
        
        taxes = []
        
        arbitration = ArbitrationSummary(
            total=2,
            cases=[
                ArbitrationCase(
                    number="A01-123/2023",
                    date_start="2023-01-01",
                    role="Ответчик",
                    amount=Decimal("50000"),
                    court="АС города Москвы",
                    instances="АС города Москвы"
                )
            ]
        )
        
        report = build_markdown_report(card, finances, taxes, arbitration)
        
        # Check that all sections are present
        assert "🧾 **Реквизиты**" in report
        assert "Test Company LLC" in report
        assert "Test LLC" in report
        assert "ИНН 1234567890" in report
        assert "ОГРН 1234567890123" in report
        assert "КПП 123456789" in report
        assert "📅 Регистрация: 2020-01-01" in report
        assert "**Статус:** ✅ Действует" in report
        assert "📍 **Адрес:** 123 Test Street, Test City" in report
        assert "🏷️ **ОКВЭД:** 62.01" in report
        assert "🧑‍💼 **Руководитель**" in report
        assert "John Doe — CEO" in report
        assert "🧩 **МСП**" in report
        assert "Является субъектом МСП" in report
        assert "📊 **Финансы**" in report
        assert "2023: выручка 1 000 000.00₽" in report
        assert "💰 **Уплаченные налоги**" in report
        assert "нет данных" in report
        assert "📄 **Арбитраж**" in report
        assert "Всего дел: 2" in report
        assert "А01-123/2023 — 2023-01-01 — Ответчик" in report
        assert "🔗 **Источники:**" in report
        assert "ЕГРЮЛ/Росстат" in report
    
    def test_render_with_minimal_data(self):
        """Test report rendering with minimal data"""
        card = CompanyCard(
            inn="1234567890",
            ogrn=None,
            kpp=None,
            name_full="Test Company",
            name_short=None,
            registration_date=None,
            status_code="UNKNOWN",
            status_text=None,
            address=None,
            manager_name=None,
            manager_post=None,
            okved=None,
            is_msme=None
        )
        
        finances = []
        taxes = []
        arbitration = ArbitrationSummary(total=0, cases=[])
        
        report = build_markdown_report(card, finances, taxes, arbitration)
        
        # Check that minimal data is handled gracefully
        assert "Test Company" in report
        assert "ИНН 1234567890" in report
        assert "ОГРН —" in report
        assert "КПП" not in report  # Should not show KPP if None
        assert "**Статус:** ❓ Неизвестно" in report
        assert "📍 **Адрес:** —" in report
        assert "🏷️ **ОКВЭД:** —" in report
        assert "—" in report  # Manager should show as dash
        assert "🧩 **МСП**" in report
        assert "—" in report  # MSME should show as dash
        assert "📊 **Финансы**" in report
        assert "Нет данных" in report
        assert "💰 **Уплаченные налоги**" in report
        assert "нет данных" in report
        assert "📄 **Арбитраж**" in report
        assert "Нет дел" in report
    
    def test_render_with_partial_finances(self):
        """Test report rendering with partial financial data"""
        card = CompanyCard(
            inn="1234567890",
            ogrn="1234567890123",
            kpp=None,
            name_full="Test Company",
            name_short=None,
            registration_date=None,
            status_code="ACTIVE",
            status_text="Действует",
            address=None,
            manager_name=None,
            manager_post=None,
            okved=None,
            is_msme=False
        )
        
        finances = [
            FinanceSnapshot(
                period="2023",
                revenue=Decimal("1000000"),
                net_profit=None,  # Missing profit
                assets=Decimal("500000"),
                equity=None,  # Missing equity
                long_term_liabilities=None,  # Missing long-term liabilities
                short_term_liabilities=Decimal("100000")
            )
        ]
        
        taxes = []
        arbitration = ArbitrationSummary(total=0, cases=[])
        
        report = build_markdown_report(card, finances, taxes, arbitration)
        
        # Check that partial financial data is handled
        assert "2023: выручка 1 000 000.00₽, прибыль N/A" in report
        assert "активы 500 000.00₽, капитал N/A" in report
        assert "долг.обяз. N/A, кратк.обяз. 100 000.00₽" in report
        assert "Не является субъектом МСП" in report
    
    def test_render_with_multiple_finance_periods(self):
        """Test report rendering with multiple finance periods"""
        card = CompanyCard(
            inn="1234567890",
            ogrn="1234567890123",
            kpp=None,
            name_full="Test Company",
            name_short=None,
            registration_date=None,
            status_code="ACTIVE",
            status_text="Действует",
            address=None,
            manager_name=None,
            manager_post=None,
            okved=None,
            is_msme=None
        )
        
        finances = [
            FinanceSnapshot(
                period="2021",
                revenue=Decimal("800000"),
                net_profit=Decimal("80000"),
                assets=Decimal("400000"),
                equity=Decimal("200000"),
                long_term_liabilities=Decimal("100000"),
                short_term_liabilities=Decimal("100000")
            ),
            FinanceSnapshot(
                period="2022",
                revenue=Decimal("900000"),
                net_profit=Decimal("90000"),
                assets=Decimal("450000"),
                equity=Decimal("250000"),
                long_term_liabilities=Decimal("100000"),
                short_term_liabilities=Decimal("100000")
            ),
            FinanceSnapshot(
                period="2023",
                revenue=Decimal("1000000"),
                net_profit=Decimal("100000"),
                assets=Decimal("500000"),
                equity=Decimal("300000"),
                long_term_liabilities=Decimal("100000"),
                short_term_liabilities=Decimal("100000")
            )
        ]
        
        taxes = []
        arbitration = ArbitrationSummary(total=0, cases=[])
        
        report = build_markdown_report(card, finances, taxes, arbitration)
        
        # Check that multiple periods are shown
        assert "2021: выручка 800 000.00₽" in report
        assert "2022: выручка 900 000.00₽" in report
        assert "2023: выручка 1 000 000.00₽" in report
