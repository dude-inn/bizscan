#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест импортов для проверки проблем
"""

print("Testing imports...")

try:
    print("1. Testing core.logger...")
    from core.logger import setup_logging
    print("✓ core.logger OK")
except Exception as e:
    print(f"✗ core.logger failed: {e}")

try:
    print("2. Testing domain.models...")
    from domain.models import CompanyBase
    print("✓ domain.models OK")
except Exception as e:
    print(f"✗ domain.models failed: {e}")

try:
    print("3. Testing services.cache...")
    from services.cache import get_cached
    print("✓ services.cache OK")
except Exception as e:
    print(f"✗ services.cache failed: {e}")

try:
    print("4. Testing services.providers.dadata...")
    from services.providers.dadata import DaDataProvider
    print("✓ services.providers.dadata OK")
except Exception as e:
    print(f"✗ services.providers.dadata failed: {e}")

try:
    print("5. Testing services.aggregator...")
    from services.aggregator import fetch_company_profile
    print("✓ services.aggregator OK")
except Exception as e:
    print(f"✗ services.aggregator failed: {e}")

try:
    print("6. Testing bot.handlers.company...")
    from bot.handlers.company import router
    print("✓ bot.handlers.company OK")
except Exception as e:
    print(f"✗ bot.handlers.company failed: {e}")

print("Import test completed!")

