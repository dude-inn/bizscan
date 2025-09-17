#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрая остановка всех Python процессов бота
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.process_manager import stop_python_processes, stop_all_python_processes

if __name__ == "__main__":
    print("🛑 Останавливаю Python процессы...")
    
    # Сначала пытаемся остановить только bizscan процессы
    count = stop_python_processes(force=True)
    
    if count == 0:
        print("⚠️  Bizscan процессы не найдены, останавливаю все Python процессы...")
        stop_all_python_processes(force=True)
    
    print("✅ Готово!")

