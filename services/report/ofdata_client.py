# -*- coding: utf-8 -*-
"""
Клиент для работы с OFData API
"""
import os
import requests
import time
from typing import Dict, Any, Optional
from core.logger import get_logger

log = get_logger(__name__)


class OFDataClient:
    """Клиент для работы с OFData API"""
    
    def __init__(self):
        """Инициализация клиента"""
        # Получаем ключ из настроек
        try:
            from core.config import load_settings
            settings = load_settings()
            self.api_key = getattr(settings, 'OFDATA_KEY', None)
        except:
            # Fallback на переменные окружения
            self.api_key = os.getenv("OFDATA_KEY")
        
        if not self.api_key:
            raise ValueError("OFDATA_KEY не найден в настройках или переменных окружения")
        
        self.base_url = "https://api.ofdata.ru/v2"
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", "15"))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BizScan/1.0',
            'Accept': 'application/json'
        })
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None, max_retries: int = 2) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к API с ретраями
        
        Args:
            endpoint: Эндпоинт API
            params: Параметры запроса
            max_retries: Максимальное количество попыток
            
        Returns:
            Ответ API
            
        Raises:
            RuntimeError: При ошибке API
        """
        if params is None:
            params = {}
        
        # Добавляем API ключ
        params['key'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                log.debug("OFDataClient: request", endpoint=endpoint, attempt=attempt+1)
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                
                # Проверяем статус ответа
                meta = data.get('meta', {})
                if meta.get('status') != 'ok':
                    error_msg = meta.get('message', 'Неизвестная ошибка API')
                    raise RuntimeError(f"API error: {error_msg}")
                
                log.debug("OFDataClient: ok", endpoint=endpoint)
                return data
                
            except requests.exceptions.RequestException as e:
                last_error = e
                log.warning("OFDataClient: request failed", endpoint=endpoint, attempt=attempt+1, error=str(e))
                
                if attempt < max_retries:
                    # Небольшой слип перед повтором
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    raise RuntimeError(f"Ошибка запроса к API: {str(e)}")
            
            except Exception as e:
                last_error = e
                log.error("OFDataClient: unexpected error", endpoint=endpoint, attempt=attempt+1, error=str(e))
                
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    raise
        
        # Если дошли сюда, значит все попытки исчерпаны
        raise RuntimeError(f"Все попытки исчерпаны. Последняя ошибка: {str(last_error)}")
    
    def get_company(self, **ident) -> Dict[str, Any]:
        """
        Получает информацию о компании
        
        Args:
            **ident: Идентификаторы (ogrn, inn, kpp, okpo)
            
        Returns:
            Данные компании
        """
        params = {}
        
        # Определяем основной идентификатор
        if 'ogrn' in ident:
            params['ogrn'] = ident['ogrn']
        elif 'inn' in ident:
            params['inn'] = ident['inn']
        elif 'okpo' in ident:
            params['okpo'] = ident['okpo']
        else:
            raise ValueError("Необходимо указать один из идентификаторов: ogrn, inn, okpo")
        
        # Добавляем дополнительные параметры
        if 'kpp' in ident:
            params['kpp'] = ident['kpp']
        
        log.info("get_company: starting", ident=ident, params=params)
        result = self._make_request('company', params)
        log.info("get_company: completed", has_data=bool(result.get('data')), keys=list(result.keys()) if result else None)
        return result
    
    def get_finances(self, **ident) -> Dict[str, Any]:
        """
        Получает финансовую отчётность
        
        Args:
            **ident: Идентификаторы (ogrn, inn, kpp, okpo)
            
        Returns:
            Финансовые данные
        """
        params = {'extended': 'true'}
        
        # Определяем основной идентификатор
        if 'ogrn' in ident:
            params['ogrn'] = ident['ogrn']
        elif 'inn' in ident:
            params['inn'] = ident['inn']
        elif 'okpo' in ident:
            params['okpo'] = ident['okpo']
        else:
            raise ValueError("Необходимо указать один из идентификаторов: ogrn, inn, okpo")
        
        # Добавляем дополнительные параметры
        if 'kpp' in ident:
            params['kpp'] = ident['kpp']
        
        return self._make_request('finances', params)
    
    def get_legal_cases(self, **ident) -> Dict[str, Any]:
        """
        Получает арбитражные дела
        
        Args:
            **ident: Идентификаторы (ogrn, inn, kpp, okpo)
            **filters: Дополнительные фильтры
            
        Returns:
            Данные арбитражных дел
        """
        params = {}
        
        # Определяем основной идентификатор
        if 'ogrn' in ident:
            params['ogrn'] = ident['ogrn']
        elif 'inn' in ident:
            params['inn'] = ident['inn']
        elif 'okpo' in ident:
            params['okpo'] = ident['okpo']
        else:
            raise ValueError("Необходимо указать один из идентификаторов: ogrn, inn, okpo")
        
        # Добавляем дополнительные параметры
        if 'kpp' in ident:
            params['kpp'] = ident['kpp']
        
        # Добавляем фильтры
        for key, value in ident.items():
            if key not in ['ogrn', 'inn', 'kpp', 'okpo'] and value is not None:
                params[key] = value
        
        return self._make_request('legal-cases', params)
    
    def get_enforcements(self, **ident) -> Dict[str, Any]:
        """
        Получает исполнительные производства
        
        Args:
            **ident: Идентификаторы (ogrn, inn, kpp, okpo)
            **filters: Дополнительные фильтры
            
        Returns:
            Данные исполнительных производств
        """
        params = {}
        
        # Определяем основной идентификатор
        if 'ogrn' in ident:
            params['ogrn'] = ident['ogrn']
        elif 'inn' in ident:
            params['inn'] = ident['inn']
        elif 'okpo' in ident:
            params['okpo'] = ident['okpo']
        else:
            raise ValueError("Необходимо указать один из идентификаторов: ogrn, inn, okpo")
        
        # Добавляем дополнительные параметры
        if 'kpp' in ident:
            params['kpp'] = ident['kpp']
        
        # Добавляем фильтры
        for key, value in ident.items():
            if key not in ['ogrn', 'inn', 'kpp', 'okpo'] and value is not None:
                params[key] = value
        
        return self._make_request('enforcements', params)
    
    def get_inspections(self, **ident) -> Dict[str, Any]:
        """
        Получает проверки
        
        Args:
            **ident: Идентификаторы (ogrn, inn, kpp, okpo)
            **filters: Дополнительные фильтры
            
        Returns:
            Данные проверок
        """
        params = {}
        
        # Определяем основной идентификатор
        if 'ogrn' in ident:
            params['ogrn'] = ident['ogrn']
        elif 'inn' in ident:
            params['inn'] = ident['inn']
        elif 'okpo' in ident:
            params['okpo'] = ident['okpo']
        else:
            raise ValueError("Необходимо указать один из идентификаторов: ogrn, inn, okpo")
        
        # Добавляем дополнительные параметры
        if 'kpp' in ident:
            params['kpp'] = ident['kpp']
        
        # Добавляем фильтры
        for key, value in ident.items():
            if key not in ['ogrn', 'inn', 'kpp', 'okpo'] and value is not None:
                params[key] = value
        
        return self._make_request('inspections', params)
    
    def get_contracts(self, law: str, role: str, **ident) -> Dict[str, Any]:
        """
        Получает контракты госзакупок
        
        Args:
            law: Закон (44, 94, 223)
            role: Роль (customer, supplier)
            **ident: Идентификаторы (ogrn, inn, kpp, okpo)
            
        Returns:
            Данные контрактов
        """
        params = {
            'law': law,
            'role': role
        }
        
        # Определяем основной идентификатор
        if 'ogrn' in ident:
            params['ogrn'] = ident['ogrn']
        elif 'inn' in ident:
            params['inn'] = ident['inn']
        elif 'okpo' in ident:
            params['okpo'] = ident['okpo']
        else:
            raise ValueError("Необходимо указать один из идентификаторов: ogrn, inn, okpo")
        
        # Добавляем дополнительные параметры
        if 'kpp' in ident:
            params['kpp'] = ident['kpp']
        
        return self._make_request('contracts', params)
    
    def get_entrepreneur(self, **ident) -> Dict[str, Any]:
        """
        Получает информацию об ИП
        
        Args:
            **ident: Идентификаторы (ogrn, inn, kpp, okpo)
            
        Returns:
            Данные ИП
        """
        params = {}
        
        # Определяем основной идентификатор
        if 'ogrn' in ident:
            params['ogrn'] = ident['ogrn']
        elif 'inn' in ident:
            params['inn'] = ident['inn']
        elif 'okpo' in ident:
            params['okpo'] = ident['okpo']
        else:
            raise ValueError("Необходимо указать один из идентификаторов: ogrn, inn, okpo")
        
        # Добавляем дополнительные параметры
        if 'kpp' in ident:
            params['kpp'] = ident['kpp']
        
        return self._make_request('entrepreneur', params)

    def get_person(self, *, inn: str) -> Dict[str, Any]:
        """
        Получает информацию о физическом лице по ИНН
        
        Args:
            inn: ИНН физического лица (обязателен)
        
        Returns:
            Данные физлица
        """
        if not inn:
            raise ValueError("Необходимо указать ИНН физического лица")
        params = {'inn': inn}
        return self._make_request('person', params)
    
    def search(self, by: str, obj: str, query: str, **opts) -> Dict[str, Any]:
        """
        Поиск по названию
        
        Args:
            by: Тип поиска (name, inn, ogrn)
            obj: Тип объекта (company, entrepreneur)
            query: Поисковый запрос
            **opts: Дополнительные опции
            
        Returns:
            Результаты поиска
        """
        params = {
            'by': by,
            'obj': obj,
            'query': query
        }
        
        # Добавляем дополнительные опции
        for key, value in opts.items():
            if value is not None:
                params[key] = value
        
        return self._make_request('search', params)
