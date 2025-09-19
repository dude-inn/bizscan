# -*- coding: utf-8 -*-
import pytest

from services.mappers.datanewton import (
    map_counterparty_to_base,
    map_finance_to_snapshots,
    find_code,
)


def test_counterparty_status_active_and_names():
    payload = {
        "inn": "3801098402",
        "ogrn": "1083801006860",
        "company": {
            "kpp": "380101001",
            "company_names": {
                "short_name": "АО \"АЭХК\"",
                "full_name": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"АНГАРСКИЙ ЭЛЕКТРОЛИЗНЫЙ ХИМИЧЕСКИЙ КОМБИНАТ\"",
            },
            "registration_date": "2008-09-01",
            "status": {
                "active_status": True,
                "status_rus_short": "Действует",
                "date_end": "",
            },
            "address": {"full_address": "Россия, Иркутская обл., Ангарск"},
            "okveds": [{"code": "35.11"}],
            "managers": [{"name": "Иванов И.И.", "position": "Генеральный директор"}],
        },
    }
    base = map_counterparty_to_base({"data": payload})
    assert base is not None
    assert base.inn == "3801098402"
    assert base.ogrn == "1083801006860"
    assert base.name_short == "АО \"АЭХК\""
    assert base.name_full.startswith("АКЦИОНЕРНОЕ ОБЩЕСТВО")
    assert base.status == "ACTIVE"
    assert base.registration_date is not None
    assert base.address is not None
    assert base.management_name == "Иванов И.И."
    assert base.management_post == "Генеральный директор"


def test_counterparty_status_liquidated():
    payload = {
        "inn": "1234567890",
        "company": {
            "company_names": {"full_name": "ООО \"Тест\""},
            "status": {"active_status": False, "date_end": "2020-01-01"},
        },
    }
    base = map_counterparty_to_base({"data": payload})
    assert base is not None
    assert base.status == "LIQUIDATED"
    assert str(base.liquidation_date) == "2020-01-01"


def test_find_code_and_finance_mapping():
    finance = {
        "balances": {
            "years": [2022, 2023, 2024],
            "assets": {
                "name": "Активы",
                "childrenMap": {
                    "totals": {"code": "1600", "sum": {"2022": 100, "2023": 200, "2024": 300}}
                },
            },
            "liabilities": {
                "childrenMap": {
                    "equity": {"code": "1300", "sum": {"2022": 10, "2023": 20, "2024": 30}},
                    "long": {"code": "1400", "sum": {"2022": 5, "2023": 6, "2024": 7}},
                    "short": {"code": "1500", "sum": {"2022": 8, "2023": 9, "2024": 10}},
                }
            },
        },
        "fin_results": {
            "indicators": [
                {"code": "2110", "sum": {"2022": 1000, "2023": 1100, "2024": 1200}},
                {"code": "2400", "sum": {"2022": 100, "2023": 120, "2024": 130}},
            ]
        },
    }

    # direct code lookup
    assets_total = find_code(finance["balances"]["assets"], "1600")
    assert assets_total and assets_total["sum"]["2024"] == 300

    snapshots = map_finance_to_snapshots(finance)
    # expect 3 snapshots, last is 2024 with numbers
    assert len(snapshots) == 3
    s2024 = [s for s in snapshots if s.period == "2024"][0]
    assert str(s2024.revenue) == "1200"
    assert str(s2024.net_profit) == "130"
    assert str(s2024.assets) == "300"
    assert str(s2024.equity) == "30"
    assert str(s2024.liabilities_long) == "7"
    assert str(s2024.liabilities_short) == "10"


