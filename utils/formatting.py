# -*- coding: utf-8 -*-
"""
Utility functions for formatting data
"""
from decimal import Decimal
from typing import Union


def format_amount(value: Union[Decimal, int, float, None]) -> str:
    """
    Format monetary amount as '1 234 567₽'
    
    Args:
        value: Amount to format (Decimal, int, float, or None)
        
    Returns:
        Formatted string with thousands separators and ruble symbol
    """
    if value is None:
        return "N/A"
    
    # Convert to Decimal for precise formatting
    if isinstance(value, (int, float)):
        amount = Decimal(str(value))
    else:
        amount = value
    
    # Round to 2 decimal places
    amount = amount.quantize(Decimal('0.01'))
    
    # Format with thousands separators
    formatted = f"{amount:,.2f}"
    
    # Replace comma with space for thousands separator (Russian style)
    formatted = formatted.replace(',', ' ')
    
    # Add ruble symbol
    return f"{formatted}₽"
