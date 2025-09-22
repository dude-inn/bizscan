# -*- coding: utf-8 -*-
"""
Рендер секции с финансами - максимально простой
"""
from typing import Dict, Any
from .simple_finances_renderer import render_finances_simple


def render_finances(data: Dict[str, Any]) -> str:
    """
    Рендерит финансы максимально просто
    
    Args:
        data: Данные финансов
        
    Returns:
        Информация о финансах
    """
    return render_finances_simple(data)