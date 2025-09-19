# -*- coding: utf-8 -*-
"""
Tests for finance mapping functions
"""
import pytest
from decimal import Decimal
from services.mappers.datanewton import map_finance as map_finance_dn
from services.mappers.ofdata import map_finance_ofdata


class TestDataNewtonFinanceMapping:
    """Test DataNewton finance mapping"""
    
    def test_map_finance_with_codes(self):
        """Test finance mapping with standard codes"""
        raw_data = {
            "data": [
                {
                    "period": "2023",
                    "balances": [
                        {"code": "1600", "value": 1000000},  # Assets
                        {"code": "1300", "value": 500000},   # Equity
                        {"code": "1400", "value": 300000},   # Long-term liabilities
                        {"code": "1500", "value": 200000},   # Short-term liabilities
                    ],
                    "fin_results": [
                        {"code": "2110", "value": 2000000},  # Revenue
                        {"code": "2400", "value": 100000},   # Net profit
                    ]
                }
            ]
        }
        
        snapshots = map_finance_dn(raw_data)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.period == "2023"
        assert snapshot.revenue == Decimal("2000000")
        assert snapshot.net_profit == Decimal("100000")
        assert snapshot.assets == Decimal("1000000")
        assert snapshot.equity == Decimal("500000")
        assert snapshot.long_term_liabilities == Decimal("300000")
        assert snapshot.short_term_liabilities == Decimal("200000")
    
    def test_map_finance_missing_codes(self):
        """Test finance mapping with missing codes"""
        raw_data = {
            "data": [
                {
                    "period": "2023",
                    "balances": [],
                    "fin_results": []
                }
            ]
        }
        
        snapshots = map_finance_dn(raw_data)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.period == "2023"
        assert snapshot.revenue is None
        assert snapshot.net_profit is None
        assert snapshot.assets is None
        assert snapshot.equity is None
        assert snapshot.long_term_liabilities is None
        assert snapshot.short_term_liabilities is None
    
    def test_map_finance_empty_data(self):
        """Test finance mapping with empty data"""
        raw_data = {"data": []}
        
        snapshots = map_finance_dn(raw_data)
        
        assert len(snapshots) == 0


class TestOFDataFinanceMapping:
    """Test OFData finance mapping"""
    
    def test_map_finance_flattened_fields(self):
        """Test OFData finance mapping with flattened fields"""
        raw_data = {
            "data": [
                {
                    "period": "2023",
                    "revenue": 2000000,
                    "profit": 100000,
                    "активы": 1000000,
                    "капитал": 500000,
                    "долгосрочные_обязательства": 300000,
                    "краткосрочные_обязательства": 200000
                }
            ]
        }
        
        snapshots = map_finance_ofdata(raw_data)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.period == "2023"
        assert snapshot.revenue == Decimal("2000000")
        assert snapshot.net_profit == Decimal("100000")
        assert snapshot.assets == Decimal("1000000")
        assert snapshot.equity == Decimal("500000")
        assert snapshot.long_term_liabilities == Decimal("300000")
        assert snapshot.short_term_liabilities == Decimal("200000")
    
    def test_map_finance_mixed_field_names(self):
        """Test OFData finance mapping with mixed field names"""
        raw_data = {
            "data": [
                {
                    "period": "2023",
                    "income": 2000000,  # Alternative revenue field
                    "net_profit": 100000,
                    "assets": 1000000,
                    "собственный_капитал": 500000,  # Alternative equity field
                    "long_term_liabilities": 300000,
                    "short_term_liabilities": 200000
                }
            ]
        }
        
        snapshots = map_finance_ofdata(raw_data)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.period == "2023"
        assert snapshot.revenue == Decimal("2000000")
        assert snapshot.net_profit == Decimal("100000")
        assert snapshot.assets == Decimal("1000000")
        assert snapshot.equity == Decimal("500000")
        assert snapshot.long_term_liabilities == Decimal("300000")
        assert snapshot.short_term_liabilities == Decimal("200000")
    
    def test_map_finance_invalid_numbers(self):
        """Test OFData finance mapping with invalid numbers"""
        raw_data = {
            "data": [
                {
                    "period": "2023",
                    "revenue": "invalid",
                    "profit": None,
                    "assets": 1000000
                }
            ]
        }
        
        snapshots = map_finance_ofdata(raw_data)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.period == "2023"
        assert snapshot.revenue is None
        assert snapshot.net_profit is None
        assert snapshot.assets == Decimal("1000000")
    
    def test_map_finance_empty_data(self):
        """Test OFData finance mapping with empty data"""
        raw_data = {"data": []}
        
        snapshots = map_finance_ofdata(raw_data)
        
        assert len(snapshots) == 0
