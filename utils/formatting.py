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


def format_rub(x: Union[float, int, None]) -> str:
    """
    Format number as Russian ruble with non-breaking spaces and comma decimal separator.
    
    Args:
        x: Number to format (float, int, or None)
        
    Returns:
        Formatted string like "1 234 567,80" or "—" for None
    """
    if x is None:
        return "—"
    
    # Convert to float and format with 2 decimal places
    try:
        num = float(x)
        formatted = f"{num:,.2f}"
        
        # Replace comma with non-breaking space for thousands separator
        # Replace decimal point with comma
        parts = formatted.split('.')
        if len(parts) == 2:
            integer_part = parts[0].replace(',', '\u00A0')  # Non-breaking space
            decimal_part = parts[1]
            return f"{integer_part},{decimal_part}"
        else:
            # No decimal part
            return parts[0].replace(',', '\u00A0')
    except (ValueError, TypeError):
        return "—"