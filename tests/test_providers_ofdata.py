# -*- coding: utf-8 -*-
"""
Tests for OFData provider
"""
import pytest
from unittest.mock import Mock, patch
from services.providers.ofdata import OFDataClient, OFDataClientError


class TestOFDataClient:
    """Test OFData client functionality"""
    
    def test_init_with_api_key(self):
        """Test client initialization with API key"""
        client = OFDataClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://ofdata.ru/api"
    
    def test_init_without_api_key(self):
        """Test client initialization without API key raises error"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(OFDataClientError, match="OFDATA_KEY"):
                OFDataClient()
    
    def test_resolve_by_query_success(self):
        """Test resolve_by_query returns INN/OGRN for successful search"""
        client = OFDataClient(api_key="test_key")
        
        mock_response = {
            "data": [
                {
                    "inn": "1234567890",
                    "ogrn": "1234567890123",
                    "name": "Test Company"
                }
            ]
        }
        
        with patch.object(client, '_get') as mock_get:
            mock_get.return_value = mock_response
            
            inn, ogrn = client.resolve_by_query("Test Company")
            
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "/v2/search"
            assert call_args[1]["params"]["query"] == "Test Company"
            assert call_args[1]["params"]["limit"] == 1
            assert "key" in call_args[1]["params"]
            
            assert inn == "1234567890"
            assert ogrn == "1234567890123"
    
    def test_resolve_by_query_no_results(self):
        """Test resolve_by_query returns None, None when no results"""
        client = OFDataClient(api_key="test_key")
        
        mock_response = {"data": []}
        
        with patch.object(client, '_get') as mock_get:
            mock_get.return_value = mock_response
            
            inn, ogrn = client.resolve_by_query("Nonexistent Company")
            
            assert inn is None
            assert ogrn is None
    
    def test_resolve_by_query_error(self):
        """Test resolve_by_query handles errors gracefully"""
        client = OFDataClient(api_key="test_key")
        
        with patch.object(client, '_get') as mock_get:
            mock_get.side_effect = OFDataClientError("API error")
            
            inn, ogrn = client.resolve_by_query("Test Company")
            
            assert inn is None
            assert ogrn is None
    
    def test_get_counterparty_inn(self):
        """Test get_counterparty with INN"""
        client = OFDataClient(api_key="test_key")
        
        with patch.object(client, '_get') as mock_get:
            mock_get.return_value = {"data": {"inn": "1234567890"}}
            
            result = client.get_counterparty(inn="1234567890")
            
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "/v2/company"
            assert call_args[1]["params"]["inn"] == "1234567890"
            assert "key" in call_args[1]["params"]
    
    def test_get_finance_inn(self):
        """Test get_finance with INN"""
        client = OFDataClient(api_key="test_key")
        
        with patch.object(client, '_get') as mock_get:
            mock_get.return_value = {"data": []}
            
            result = client.get_finance(inn="1234567890")
            
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "/v2/finances"
            assert call_args[1]["params"]["inn"] == "1234567890"
            assert "key" in call_args[1]["params"]
    
    def test_get_paid_taxes_returns_empty(self):
        """Test get_paid_taxes returns empty data (not supported)"""
        client = OFDataClient(api_key="test_key")
        
        result = client.get_paid_taxes(inn="1234567890")
        
        assert result == {"data": [], "available_count": 0}
    
    def test_get_arbitration_cases_inn(self):
        """Test get_arbitration_cases with INN"""
        client = OFDataClient(api_key="test_key")
        
        with patch.object(client, '_get') as mock_get:
            mock_get.return_value = {"data": []}
            
            result = client.get_arbitration_cases(inn="1234567890")
            
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "/v2/legal-cases"
            assert call_args[1]["params"]["inn"] == "1234567890"
            assert call_args[1]["params"]["limit"] == 1000
            assert call_args[1]["params"]["offset"] == 0
            assert "key" in call_args[1]["params"]
