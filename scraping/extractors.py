# -*- coding: utf-8 -*-
import re
import yaml
from typing import List, Optional, Dict, Any, Union
from bs4 import BeautifulSoup, Tag, NavigableString
from pathlib import Path
from core.logger import setup_logging

log = setup_logging()

# Загружаем конфигурацию лейблов
LABELS_CONFIG = None
def load_labels_config():
    global LABELS_CONFIG
    if LABELS_CONFIG is None:
        config_path = Path(__file__).parent / "labels.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                LABELS_CONFIG = yaml.safe_load(f)
        except Exception as e:
            log.error("Failed to load labels config", exc_info=e)
            LABELS_CONFIG = {}
    return LABELS_CONFIG

def find_by_label(soup: BeautifulSoup, labels: List[str]) -> Optional[str]:
    """
    Ищет значение справа/ниже от лейбла.
    Поддерживает различные варианты написания.
    """
    if not labels:
        return None
    
    config = load_labels_config()
    
    # Ищем элемент, содержащий один из лейблов
    for label in labels:
        # Поиск по точному тексту
        elements = soup.find_all(text=re.compile(re.escape(label), re.IGNORECASE))
        
        for element in elements:
            if isinstance(element, NavigableString):
                parent = element.parent
            else:
                parent = element
            
            if not parent:
                continue
            
            # Ищем значение в соседних элементах
            value = _extract_value_from_element(parent, label)
            if value:
                return value.strip()
            
            # Ищем в родительском элементе
            if parent.parent:
                value = _extract_value_from_element(parent.parent, label)
                if value:
                    return value.strip()
    
    return None

def _extract_value_from_element(element: Tag, label: str) -> Optional[str]:
    """Извлекает значение из элемента относительно лейбла"""
    if not element:
        return None
    
    # Ищем в следующих элементах
    current = element.next_sibling
    while current:
        if isinstance(current, NavigableString):
            text = current.strip()
            if text and text != label:
                return text
        elif isinstance(current, Tag):
            text = current.get_text(strip=True)
            if text and text != label:
                return text
        current = current.next_sibling
    
    # Ищем в дочерних элементах
    for child in element.find_all(['span', 'div', 'td', 'li']):
        text = child.get_text(strip=True)
        if text and text != label and len(text) > len(label):
            return text
    
    return None

def extract_contacts(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Извлекает контактную информацию"""
    config = load_labels_config()
    contacts_config = config.get('contacts', {})
    contacts = {}
    
    for contact_type, labels in contacts_config.items():
        values = []
        for label in labels:
            value = find_by_label(soup, [label])
            if value:
                # Разбиваем множественные контакты
                if contact_type == 'phone':
                    # Телефоны могут быть через запятую или в разных строках
                    phones = re.split(r'[,;]', value)
                    values.extend([p.strip() for p in phones if p.strip()])
                else:
                    values.append(value)
        
        if values:
            contacts[contact_type] = list(set(values))  # убираем дубликаты
    
    return contacts

def extract_stats_codes(soup: BeautifulSoup) -> Dict[str, str]:
    """Извлекает коды статистики"""
    config = load_labels_config()
    stats_config = config.get('stats_codes', {})
    codes = {}
    
    for code_type, labels in stats_config.items():
        value = find_by_label(soup, labels)
        if value:
            # Очищаем от лишних символов
            cleaned = re.sub(r'[^\d]', '', value)
            if cleaned:
                codes[code_type] = cleaned
    
    return codes

def extract_okveds(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Извлекает коды ОКВЭД"""
    okveds = {'main': [], 'additional': []}
    
    # Поиск основного ОКВЭД
    main_labels = ["Основной вид деятельности", "Основной ОКВЭД", "Основной код ОКВЭД"]
    main_value = find_by_label(soup, main_labels)
    if main_value:
        # Извлекаем код ОКВЭД из текста
        okved_codes = re.findall(r'\d{2}\.\d{2}(?:\.\d{2})?', main_value)
        okveds['main'] = okved_codes
    
    # Поиск дополнительных ОКВЭД
    # Ищем таблицы или списки с кодами
    tables = soup.find_all(['table', 'ul', 'ol'])
    for table in tables:
        text = table.get_text()
        if 'ОКВЭД' in text or 'вид деятельности' in text:
            codes = re.findall(r'\d{2}\.\d{2}(?:\.\d{2})?', text)
            okveds['additional'].extend(codes)
    
    # Убираем дубликаты
    okveds['main'] = list(set(okveds['main']))
    okveds['additional'] = list(set(okveds['additional']))
    
    return okveds

def extract_founders_directors(soup: BeautifulSoup) -> Dict[str, List[Dict[str, str]]]:
    """Извлекает информацию об учредителях и руководителях"""
    result = {'founders': [], 'directors': []}
    
    # Поиск учредителей
    founder_sections = soup.find_all(text=re.compile(r'учредител', re.IGNORECASE))
    for section in founder_sections:
        if isinstance(section, NavigableString):
            parent = section.parent
        else:
            parent = section
        
        if parent:
            # Ищем таблицы или списки с учредителями
            tables = parent.find_all(['table', 'ul', 'ol'])
            for table in tables:
                rows = table.find_all('tr') if table.name == 'table' else table.find_all('li')
                for row in rows:
                    text = row.get_text(strip=True)
                    if text and len(text) > 10:  # фильтруем короткие строки
                        result['founders'].append({'name': text, 'share': ''})
    
    # Поиск руководителей
    director_labels = ["Руководитель", "Генеральный директор", "Директор"]
    for label in director_labels:
        value = find_by_label(soup, [label])
        if value:
            result['directors'].append({'name': value, 'position': label})
    
    return result

def extract_finance_table(soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
    """Извлекает финансовые данные по годам"""
    finance = {}
    config = load_labels_config()
    finance_config = config.get('finance', {})
    
    # Ищем таблицы с финансовыми данными
    tables = soup.find_all('table')
    for table in tables:
        text = table.get_text()
        if any(keyword in text.lower() for keyword in ['выручка', 'прибыль', 'активы', 'обязательства']):
            # Парсим таблицу
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Первая строка - заголовки
            headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
            
            # Ищем колонку с годами
            year_col = None
            for i, header in enumerate(headers):
                if re.match(r'^\d{4}$', header):
                    year_col = i
                    break
            
            if year_col is None:
                continue
            
            # Парсим данные по строкам
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if len(cells) <= year_col:
                    continue
                
                year = cells[year_col]
                if not re.match(r'^\d{4}$', year):
                    continue
                
                # Ищем тип финансового показателя в первой колонке
                indicator = cells[0].lower()
                for finance_type, keywords in finance_config.items():
                    if any(keyword.lower() in indicator for keyword in keywords):
                        # Ищем значение в колонке года
                        if year_col + 1 < len(cells):
                            value = cells[year_col + 1]
                            if year not in finance:
                                finance[year] = {}
                            finance[year][finance_type] = value
                        break
    
    return finance

def extract_legal_flags(soup: BeautifulSoup) -> Dict[str, bool]:
    """Извлекает правовые индикаторы"""
    flags = {}
    
    # Список индикаторов для поиска
    indicators = [
        'массовый руководитель',
        'массовый учредитель',
        'недостоверность адреса',
        'недостоверность руководителя',
        'недостоверность учредителя',
        'налоговая задолженность',
        'дисквалифицированные лица',
        'недобросовестные поставщики'
    ]
    
    page_text = soup.get_text().lower()
    
    for indicator in indicators:
        flags[indicator] = indicator in page_text
    
    return flags

def extract_licenses(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Извлекает информацию о лицензиях"""
    licenses = []
    
    # Ищем секции с лицензиями
    license_sections = soup.find_all(text=re.compile(r'лиценз', re.IGNORECASE))
    for section in license_sections:
        if isinstance(section, NavigableString):
            parent = section.parent
        else:
            parent = section
        
        if parent:
            # Ищем таблицы или списки с лицензиями
            tables = parent.find_all(['table', 'ul', 'ol'])
            for table in tables:
                rows = table.find_all('tr') if table.name == 'table' else table.find_all('li')
                for row in rows:
                    text = row.get_text(strip=True)
                    if text and len(text) > 10:
                        licenses.append({
                            'type': text,
                            'number': '',
                            'date': '',
                            'authority': ''
                        })
    
    return licenses

def extract_company_basic_info(soup: BeautifulSoup) -> Dict[str, str]:
    """Извлекает основную информацию о компании"""
    config = load_labels_config()
    info = {}
    
    # Извлекаем поля по конфигурации
    for field, labels in config.items():
        if field in ['stats_codes', 'contacts', 'finance']:
            continue  # эти поля обрабатываются отдельно
        
        value = find_by_label(soup, labels)
        if value:
            info[field] = value
    
    return info



