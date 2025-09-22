# -*- coding: utf-8 -*-
"""
OpenAI провайдер для генерации истории компании и резюме
"""
import os
from typing import Dict, Any, Optional
from openai import OpenAI
from loguru import logger
from dotenv import load_dotenv
from pathlib import Path

# Загружаем .env файл
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class OpenAIProvider:
    """OpenAI провайдер для генерации текста"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL_GAMMA", "gpt-4o-mini")
        self.client = None
        
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            logger.warning("OPENAI_API_KEY not set - OpenAI features disabled")
    
    def _extract_basic_company_data(self, report_text: str) -> Dict[str, str]:
        """Извлекает основные данные компании из отчета"""
        import re
        
        # Извлекаем название компании
        name_match = re.search(r'НАЗВАНИЕ:\s*(.+?)(?:\n|$)', report_text, re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else "Не указано"
        
        # Извлекаем ИНН
        inn_match = re.search(r'ИНН:\s*(\d+)', report_text, re.IGNORECASE)
        inn = inn_match.group(1) if inn_match else "Не указан"
        
        # Извлекаем адрес - ищем разные варианты
        address = "Не указан"
        
        # Вариант 1: Юридический адрес
        address_match = re.search(r'Юридический адрес:\s*(.+?)(?:\n|$)', report_text, re.IGNORECASE)
        if address_match:
            address = address_match.group(1).strip()
        else:
            # Вариант 2: ЮрАдрес
            address_match = re.search(r'ЮрАдрес:\s*(.+?)(?:\n|$)', report_text, re.IGNORECASE)
            if address_match:
                address = address_match.group(1).strip()
            else:
                # Вариант 3: Адрес
                address_match = re.search(r'Адрес:\s*(.+?)(?:\n|$)', report_text, re.IGNORECASE)
                if address_match:
                    address = address_match.group(1).strip()
        
        return {
            "name": name,
            "inn": inn,
            "address": address
        }
    
    async def generate_company_history(self, report_text: str) -> str:
        """Генерирует историю компании на основе отчета"""
        if not self.client:
            return "История компании недоступна (OpenAI не настроен)"
        
        try:
            # Извлекаем основные данные из отчета
            company_data = self._extract_basic_company_data(report_text)
            
              system_prompt = """Ты — аналитик. Сформируй краткие блоки на основе указанных реквизитов компании.
            
      Сформируй и предоставь:
- Общие сведения о компании
- История развития
- Значимые факты и достижения
- Текущая деятельность

      Формат ответа:
      — Краткое описание предполагаемой деятельности и местоположения (без ссылок)
      — 2-3 аккуратных факта, сформулированных без утверждений о внешнем поиске

Стиль: нейтральный, информативный."""

              user_prompt = f"""Сформируй краткое описание и сводку по компании на основе реквизитов:
- Название: {company_data['name']}
- Адрес: {company_data['address']}  
- ИНН: {company_data['inn']}

      Сформируй и предоставь:
- Общие сведения о компании
- История развития
- Значимые факты и достижения
- Текущая деятельность"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI history generation failed: {e}")
            return "Ошибка генерации истории компании"
    
    async def generate_company_summary(self, report_text: str) -> str:
        """Генерирует резюме компании на основе отчета"""
        if not self.client:
            return "Резюме недоступно (OpenAI не настроен)"
        
        try:
            # Извлекаем основные данные из отчета
            company_data = self._extract_basic_company_data(report_text)
            
            system_prompt = """Ты — аналитик. Проведи поиск в интернете и найди информацию по компании.
            
Найди и предоставь:
- Общие сведения о компании
- История развития
- Значимые факты и достижения
- Текущая деятельность

Формат ответа:
— Краткое описание деятельности и местоположения
— 3-5 ключевых фактов о компании
— Источники информации

Стиль: нейтральный, информативный."""

            user_prompt = f"""Проведи поиск в интернете и найди информацию по компании:
- Название: {company_data['name']}
- Адрес: {company_data['address']}  
- ИНН: {company_data['inn']}

Найди и предоставь:
- Общие сведения о компании
- История развития
- Значимые факты и достижения
- Текущая деятельность"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI summary generation failed: {e}")
            return "Ошибка генерации резюме"
