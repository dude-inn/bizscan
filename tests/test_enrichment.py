# -*- coding: utf-8 -*-
"""
Tests for enrichment modules
"""
import pytest
from unittest.mock import patch, Mock
from services.enrichment.openai_gamma_enricher import generate_gamma_section, build_user_prompt
from bot.formatters.gamma_insert import build_gamma_block_for_company


class TestSearchProvidersRemoved:
    def test_search_providers_module_removed(self):
        with pytest.raises(ModuleNotFoundError):
            __import__('services.enrichment.search_providers')


class TestOpenAIGammaEnricher:
    """Test OpenAI Gamma enricher functionality"""
    
    def test_build_user_prompt(self):
        """Test user prompt building"""
        company = {
            "name_full": "Test Company LLC",
            "inn": "1234567890",
            "ogrn": "1234567890123",
            "okved": "62.01",
            "address": "Moscow, Russia"
        }
        
        snippets = [
            {
                "title": "Test News",
                "url": "https://test.com/news",
                "snippet": "Test snippet about company"
            }
        ]
        
        prompt = build_user_prompt(company, snippets)
        
        assert "Test Company LLC" in prompt
        assert "ИНН 1234567890" in prompt
        assert "ОГРН 1234567890123" in prompt
        assert "ОКВЭД: 62.01" in prompt
        assert "локация: Moscow" in prompt
        assert "Test News" in prompt
        assert "https://test.com/news" in prompt
    
    def test_generate_gamma_section_no_api_key(self):
        """Test gamma section generation without API key"""
        with patch.dict('os.environ', {}, clear=True):
            company = {"name_full": "Test Company"}
            snippets = [{"url": "https://test.com", "title": "Test"}]
            
            result = generate_gamma_section(company, snippets)
            
            assert "Test Company" in result
            assert "_Добавьте OPENAI_API_KEY" in result
            assert "https://test.com" in result
    
    def test_generate_gamma_section_with_api_key(self):
        """Test gamma section generation with API key"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}, clear=True):
        with patch('openai.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = "Generated content"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                company = {"name_full": "Test Company"}
                snippets = [{"url": "https://test.com", "title": "Test"}]
                
                result = generate_gamma_section(company, snippets)
                
                assert result == "Generated content"
                mock_client.chat.completions.create.assert_called_once()


class TestGammaInsert:
    """Test Gamma insert functionality"""
    
    def test_build_gamma_block_for_company(self):
        """Test building gamma block for company"""
        with patch('services.enrichment.openai_gamma_enricher.generate_gamma_section') as mock_generate:
            mock_generate.return_value = "Generated gamma content"
                
                company = {
                    "name_full": "Test Company",
                    "name_short": "Test",
                    "inn": "1234567890",
                    "ogrn": "1234567890123",
                    "okved": "62.01",
                    "address": "Moscow"
                }
                
                result = build_gamma_block_for_company(company)
                
                assert result == "Generated gamma content"
                mock_generate.assert_called_once()
    
    def test_build_gamma_block_fallback_name(self):
        """Test building gamma block with fallback to INN/OGRN"""
        with patch('services.enrichment.openai_gamma_enricher.generate_gamma_section') as mock_generate:
            mock_generate.return_value = "Generated content"
                
                company = {
                    "name_full": "",
                    "inn": "1234567890",
                    "ogrn": "1234567890123"
                }
                
                result = build_gamma_block_for_company(company)
                
                assert result == "Generated content"
