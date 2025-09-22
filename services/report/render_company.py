# -*- coding: utf-8 -*-
"""
Рендер секции с информацией о компании - максимально простой
"""
from typing import Dict, Any
from .simple_company_renderer import render_company_simple


def render_company(data: Dict[str, Any]) -> str:
    """
    Рендерит информацию о компании максимально просто
    
    Args:
        data: Данные компании
        
    Returns:
        Информация о компании
    """
    return render_company_simple(data)
