# -*- coding: utf-8 -*-
"""
Тесты для провайдеров данных
"""
import pytest
import responses
from unittest.mock import patch, AsyncMock

from services.providers.dadata import DaDataProvider, DaDataConfig
from services.providers.msme import MsmeProvider, MsmeConfig
from services.providers.efrsb import EfrsbProvider, EfrsbConfig
from services.providers.kad import KadProvider, KadConfig
from domain.models import CompanyBase, MsmeInfo, BankruptcyInfo, ArbitrationInfo


class TestDaDataProvider:
    """Тесты для DaData провайдера"""
    
    @pytest.fixture
    def config(self):
        return DaDataConfig(api_key="test_key")
    
    @pytest.fixture
    def provider(self, config):
        return DaDataProvider(config)
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_suggest_party(self, provider):
        """Тест поиска компаний"""
        responses.add(
            responses.POST,
            "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party",
            json={
                "suggestions": [
                    {
                        "value": "ООО Тест",
                        "data": {
                            "inn": "1234567890",
                            "name": {"full_with_opf": "ООО Тест"},
                            "address": {"value": "Москва"},
                            "state": {"status": "ACTIVE"}
                        }
                    }
                ]
            },
            status=200
        )
        
        async with provider:
            result = await provider.suggest_party("ООО Тест")
            assert len(result) == 1
            assert result[0]["value"] == "ООО Тест"
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_find_party(self, provider):
        """Тест поиска по ИНН"""
        responses.add(
            responses.POST,
            "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party",
            json={
                "suggestions": [
                    {
                        "value": "ООО Тест",
                        "data": {
                            "inn": "1234567890",
                            "ogrn": "1234567890123",
                            "name": {"full_with_opf": "ООО Тест"},
                            "address": {"value": "Москва", "qc": "0"},
                            "state": {"status": "ACTIVE", "registration_date": "2020-01-01T00:00:00Z"},
                            "management": {"name": "Иванов И.И.", "post": "Генеральный директор"},
                            "okved": "62.01",
                            "capital": "10000"
                        }
                    }
                ]
            },
            status=200
        )
        
        async with provider:
            result = await provider.find_party("1234567890")
            assert result is not None
            assert result["data"]["inn"] == "1234567890"
    
    def test_parse_company_data(self, provider):
        """Тест парсинга данных компании"""
        data = {
            "data": {
                "inn": "1234567890",
                "ogrn": "1234567890123",
                "name": {"full_with_opf": "ООО Тест"},
                "address": {"value": "Москва", "qc": "0"},
                "state": {"status": "ACTIVE", "registration_date": "2020-01-01T00:00:00Z"},
                "management": {"name": "Иванов И.И.", "post": "Генеральный директор"},
                "okved": "62.01",
                "capital": "10000"
            }
        }
        
        company = provider.parse_company_data(data)
        assert isinstance(company, CompanyBase)
        assert company.inn == "1234567890"
        assert company.name_full == "ООО Тест"
        assert company.status == "ACTIVE"


class TestMsmeProvider:
    """Тесты для МСП провайдера"""
    
    @pytest.fixture
    def config(self):
        return MsmeConfig(local_file="tests/fixtures/msme_sample.csv")
    
    @pytest.fixture
    def provider(self, config):
        return MsmeProvider(config)
    
    @pytest.mark.asyncio
    async def test_get_msme_status_found(self, provider):
        """Тест получения статуса МСП - найдено"""
        # Мокаем загрузку данных
        import pandas as pd
        test_data = pd.DataFrame({
            'ИНН': ['1234567890'],
            'Категория': ['малое предприятие'],
            'Период': ['2024-12']
        })
        
        with patch.object(provider, '_load_data', return_value=test_data):
            result = await provider.get_msme_status("1234567890")
            assert result.is_msme is True
            assert result.category == "small"
            assert result.period == "2024-12"
    
    @pytest.mark.asyncio
    async def test_get_msme_status_not_found(self, provider):
        """Тест получения статуса МСП - не найдено"""
        import pandas as pd
        test_data = pd.DataFrame({
            'ИНН': ['9999999999'],
            'Категория': ['малое предприятие'],
            'Период': ['2024-12']
        })
        
        with patch.object(provider, '_load_data', return_value=test_data):
            result = await provider.get_msme_status("1234567890")
            assert result.is_msme is False


class TestEfrsbProvider:
    """Тесты для ЕФРСБ провайдера"""
    
    @pytest.fixture
    def config(self):
        return EfrsbConfig(api_url="https://test.com", api_key="test_key", enabled=True)
    
    @pytest.fixture
    def provider(self, config):
        return EfrsbProvider(config)
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_check_bankruptcy_found(self, provider):
        """Тест проверки банкротства - найдено"""
        responses.add(
            responses.POST,
            "https://test.com/search",
            json={
                "records": [
                    {
                        "number": "А40-12345/2024",
                        "stage": "Наблюдение",
                        "date": "2024-01-01"
                    }
                ]
            },
            status=200
        )
        
        async with provider:
            result = await provider.check_bankruptcy("1234567890")
            assert result.has_bankruptcy_records is True
            assert len(result.records) == 1
            assert result.records[0]["number"] == "А40-12345/2024"
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_check_bankruptcy_not_found(self, provider):
        """Тест проверки банкротства - не найдено"""
        responses.add(
            responses.POST,
            "https://test.com/search",
            json={"records": []},
            status=200
        )
        
        async with provider:
            result = await provider.check_bankruptcy("1234567890")
            assert result.has_bankruptcy_records is False
            assert len(result.records) == 0


class TestKadProvider:
    """Тесты для КАД провайдера"""
    
    @pytest.fixture
    def config(self):
        return KadConfig(api_url="https://test.com", api_key="test_key", enabled=True, max_cases=5)
    
    @pytest.fixture
    def provider(self, config):
        return KadProvider(config)
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_get_arbitration_cases_found(self, provider):
        """Тест получения арбитражных дел - найдено"""
        responses.add(
            responses.POST,
            "https://test.com/search",
            json={
                "total": 2,
                "cases": [
                    {
                        "id": "1",
                        "number": "А40-12345/2024",
                        "date": "2024-01-01",
                        "roles": ["истец"],
                        "instance": "1 инстанция",
                        "url": "https://example.com/case/1"
                    },
                    {
                        "id": "2", 
                        "number": "А40-67890/2024",
                        "date": "2024-02-01",
                        "roles": ["ответчик"],
                        "instance": "1 инстанция",
                        "url": "https://example.com/case/2"
                    }
                ]
            },
            status=200
        )
        
        async with provider:
            result = await provider.get_arbitration_cases("1234567890")
            assert result.total == 2
            assert len(result.cases) == 2
            assert result.cases[0]["number"] == "А40-12345/2024"
    
    @responses.activate
    @pytest.mark.asyncio
    async def test_get_arbitration_cases_not_found(self, provider):
        """Тест получения арбитражных дел - не найдено"""
        responses.add(
            responses.POST,
            "https://test.com/search",
            json={"total": 0, "cases": []},
            status=200
        )
        
        async with provider:
            result = await provider.get_arbitration_cases("1234567890")
            assert result.total == 0
            assert len(result.cases) == 0

