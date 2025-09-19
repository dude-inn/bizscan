# -*- coding: utf-8 -*-
"""
Tests for status mapping functions
"""
import pytest
from services.mappers.datanewton import map_status as map_status_dn
from services.mappers.ofdata import map_status_ofdata


class TestDataNewtonStatusMapping:
    """Test DataNewton status mapping"""
    
    def test_active_status_true(self):
        """Test active_status true maps to ACTIVE"""
        status_obj = {
            "active_status": True,
            "status_rus_short": "Действует"
        }
        
        code, text = map_status_dn(status_obj)
        assert code == "ACTIVE"
        assert text == "Действует"
    
    def test_active_status_false_with_date_end(self):
        """Test active_status false with date_end maps to LIQUIDATED"""
        status_obj = {
            "active_status": False,
            "date_end": "2023-01-01",
            "status_rus_short": "Ликвидировано"
        }
        
        code, text = map_status_dn(status_obj)
        assert code == "LIQUIDATED"
        assert text == "Ликвидировано"
    
    def test_active_status_false_no_date_end(self):
        """Test active_status false without date_end maps to NOT_ACTIVE"""
        status_obj = {
            "active_status": False,
            "date_end": "",
            "status_rus_short": "Не действует"
        }
        
        code, text = map_status_dn(status_obj)
        assert code == "NOT_ACTIVE"
        assert text == "Не действует"
    
    def test_unknown_status(self):
        """Test unknown status maps to UNKNOWN"""
        status_obj = {
            "status_rus_short": "Неизвестно"
        }
        
        code, text = map_status_dn(status_obj)
        assert code == "UNKNOWN"
        assert text == "Неизвестно"


class TestOFDataStatusMapping:
    """Test OFData status mapping"""
    
    def test_deystvuyushchee_maps_to_active(self):
        """Test 'действующ' status maps to ACTIVE"""
        status_obj = {
            "status": "действующее",
            "status_rus": "Действует"
        }
        
        code, text = map_status_ofdata(status_obj)
        assert code == "ACTIVE"
        assert text == "Действует"
    
    def test_likvidirovano_maps_to_liquidated(self):
        """Test 'ликвидирован' status maps to LIQUIDATED"""
        status_obj = {
            "status": "ликвидировано",
            "status_rus": "Ликвидировано"
        }
        
        code, text = map_status_ofdata(status_obj)
        assert code == "LIQUIDATED"
        assert text == "Ликвидировано"
    
    def test_ne_deystvuet_maps_to_not_active(self):
        """Test 'не действует' status maps to NOT_ACTIVE"""
        status_obj = {
            "status": "не действует",
            "status_rus": "Не действует"
        }
        
        code, text = map_status_ofdata(status_obj)
        assert code == "NOT_ACTIVE"
        assert text == "Не действует"
    
    def test_unknown_status_maps_to_unknown(self):
        """Test unknown status maps to UNKNOWN"""
        status_obj = {
            "status": "неизвестно",
            "status_rus": "Неизвестно"
        }
        
        code, text = map_status_ofdata(status_obj)
        assert code == "UNKNOWN"
        assert text == "Неизвестно"
    
    def test_empty_status(self):
        """Test empty status maps to UNKNOWN"""
        status_obj = {}
        
        code, text = map_status_ofdata(status_obj)
        assert code == "UNKNOWN"
        assert text is None
