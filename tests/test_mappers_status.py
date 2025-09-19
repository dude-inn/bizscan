# -*- coding: utf-8 -*-
"""
Tests for status mapping functions
"""
import pytest
from services.mappers.ofdata import map_status_ofdata


class TestDataNewtonRemoved:
    def test_dn_mapper_removed(self):
        import pytest
        with pytest.raises(ModuleNotFoundError):
            __import__("services.mappers.datanewton")


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
