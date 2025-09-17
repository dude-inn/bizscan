#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест PDF генерации
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from domain.models import CompanyFull
from reports.pdf import generate_pdf

def test_pdf_generation():
    print("=== НАЧАЛО ТЕСТА PDF ===")
    
    try:
        print("1. Создаю тестовую компанию...")
        # Создаем тестовую компанию
        company = CompanyFull(
            short_name="OOO TSO",
            full_name="Obshchestvo s ogranichennoy otvetstvennostyu Tsentr servisnogo obsluzhivaniya",
            inn="3812150012",
            ogrn="1023800000012",
            kpp="381201001",
            status="Deystvuyushchee",
            reg_date="15.01.2002",
            address="g. Irkutsk, ul. Lenina, d. 1",
            director="Ivanov Ivan Ivanovich",
            source_url="/test"
        )
        print("2. Компания создана успешно")
        
        print("3. Импортирую generate_pdf...")
        from reports.pdf import generate_pdf
        print("4. Импорт успешен")
        
        print("5. Генерирую PDF...")
        # Генерируем PDF
        pdf_bytes = generate_pdf(company, "free")
        print(f"6. ✅ PDF сгенерирован успешно! Размер: {len(pdf_bytes)} байт")
        
        print("7. Сохраняю PDF...")
        # Сохраняем для проверки
        with open("test_report.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("8. ✅ PDF сохранен как test_report.pdf")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_pdf_generation()
