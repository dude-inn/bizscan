# -*- coding: utf-8 -*-
"""
Рендер секции с госзакупками - максимально простой
"""
from typing import Dict, Any
from .simple_contracts_renderer import render_contracts_simple


def render_contracts(data: Dict[str, Any]) -> str:
    """
    Рендерит госзакупки максимально просто
    
    Args:
        data: Данные контрактов
        
    Returns:
        Информация о контрактах
    """
    return render_contracts_simple(data)