# -*- coding: utf-8 -*-
"""
Security utilities for logging and data handling
"""
import re
from typing import Any, Dict


def redact_api_keys(data: Any) -> Any:
    """
    Redact API keys from data before logging
    
    Args:
        data: Data structure that might contain API keys
        
    Returns:
        Data with API keys redacted
    """
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            # Check if key looks like an API key field
            if _is_api_key_field(key):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)):
                redacted[key] = redact_api_keys(value)
            else:
                redacted[key] = value
        return redacted
    elif isinstance(data, list):
        return [redact_api_keys(item) for item in data]
    else:
        return data


def _is_api_key_field(key: str) -> bool:
    """
    Check if a field name looks like an API key field
    
    Args:
        key: Field name to check
        
    Returns:
        True if field should be redacted
    """
    key_lower = key.lower()
    api_key_patterns = [
        'api_key', 'apikey', 'api-key',
        'access_token', 'accesstoken', 'access-token',
        'secret', 'password', 'passwd',
        'token', 'auth', 'authorization',
        'key', 'private_key', 'privatekey'
    ]
    
    return any(pattern in key_lower for pattern in api_key_patterns)


def safe_log_data(data: Any, max_length: int = 1000) -> str:
    """
    Safely log data by redacting sensitive information and limiting length
    
    Args:
        data: Data to log
        max_length: Maximum length of logged data
        
    Returns:
        Safe string for logging
    """
    redacted = redact_api_keys(data)
    data_str = str(redacted)
    
    if len(data_str) > max_length:
        data_str = data_str[:max_length] + "..."
    
    return data_str
