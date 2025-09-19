# -*- coding: utf-8 -*-
"""
Tests for validation functions
"""
import pytest
from services.aggregator import _detect_id_kind


class TestIDValidator:
    """Test INN/OGRN validation"""
    
    def test_valid_inn_10_digits(self):
        """Test 10-digit INN validation"""
        kind, value = _detect_id_kind("1234567890")
        assert kind == "inn"
        assert value == "1234567890"
    
    def test_valid_inn_12_digits(self):
        """Test 12-digit INN validation"""
        kind, value = _detect_id_kind("123456789012")
        assert kind == "inn"
        assert value == "123456789012"
    
    def test_valid_ogrn_13_digits(self):
        """Test 13-digit OGRN validation"""
        kind, value = _detect_id_kind("1234567890123")
        assert kind == "ogrn"
        assert value == "1234567890123"
    
    def test_valid_ogrn_15_digits(self):
        """Test 15-digit OGRN validation"""
        kind, value = _detect_id_kind("123456789012345")
        assert kind == "ogrn"
        assert value == "123456789012345"
    
    def test_invalid_short_inn(self):
        """Test invalid short INN"""
        kind, value = _detect_id_kind("123456789")
        assert kind == ""
        assert value == ""
    
    def test_invalid_long_inn(self):
        """Test invalid long INN"""
        kind, value = _detect_id_kind("12345678901")
        assert kind == ""
        assert value == ""
    
    def test_invalid_short_ogrn(self):
        """Test invalid short OGRN"""
        kind, value = _detect_id_kind("123456789012")
        assert kind == "inn"  # 12 digits is valid INN
        assert value == "123456789012"
    
    def test_invalid_long_ogrn(self):
        """Test invalid long OGRN"""
        kind, value = _detect_id_kind("1234567890123456")
        assert kind == ""
        assert value == ""
    
    def test_non_digit_input(self):
        """Test non-digit input"""
        kind, value = _detect_id_kind("abc123def")
        assert kind == ""
        assert value == ""
    
    def test_empty_input(self):
        """Test empty input"""
        kind, value = _detect_id_kind("")
        assert kind == ""
        assert value == ""
    
    def test_whitespace_input(self):
        """Test whitespace input"""
        kind, value = _detect_id_kind("  1234567890  ")
        assert kind == "inn"
        assert value == "1234567890"
    
    def test_mixed_chars(self):
        """Test input with mixed characters"""
        kind, value = _detect_id_kind("123-456-789-0")
        assert kind == "inn"
        assert value == "1234567890"
