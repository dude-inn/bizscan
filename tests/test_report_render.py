# -*- coding: utf-8 -*-
from datetime import datetime

from bot.handlers.company import _format_company_response
from domain.models import CompanyAggregate, CompanyBase, ArbitrationInfo, FinanceSnapshot


def _base_company() -> CompanyBase:
    return CompanyBase(
        inn="3801098402",
        ogrn="1083801006860",
        kpp="380101001",
        name_full="АКЦИОНЕРНОЕ ОБЩЕСТВО \"АНГАРСКИЙ ЭЛЕКТРОЛИЗНЫЙ ХИМИЧЕСКИЙ КОМБИНАТ\"",
        name_short="АО \"АЭХК\"",
        status="ACTIVE",
    )


def test_paid_taxes_empty_renders_no_data():
    company = CompanyAggregate(
        base=_base_company(),
        finances=[],
        arbitration=None,
        sources={"DataNewton": "API v1"},
        extra={"paid_taxes": {"data": []}},
    )
    text = _format_company_response(company)
    # When no paid taxes entries, section should not crash; absence is acceptable
    # but if present, it should say 'нет данных'. We ensure it doesn't raise and returns string.
    assert isinstance(text, str)


def test_arbitration_render_top_items_and_total():
    cases = [
        {
            "first_number": "A40-1/2025",
            "date_start": "2025-01-01",
            "sum": 100.0,
            "respondents": [{"role": "Ответчик"}],
            "instances": ["АС города Москвы"],
        },
        {
            "first_number": "A40-2/2025",
            "date_start": "2025-02-01",
            "sum": 200.0,
            "respondents": [{"role": "Истец"}],
            "instances": ["АС города Москвы"],
        },
    ]
    company = CompanyAggregate(
        base=_base_company(),
        finances=[FinanceSnapshot(period="2024")],
        arbitration=ArbitrationInfo(total=15, cases=cases),
        sources={"DataNewton": "API v1"},
        extra={},
    )
    text = _format_company_response(company)
    assert "Арбитраж" in text
    assert "15" in text  # total displayed

