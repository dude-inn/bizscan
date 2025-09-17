#!/usr/bin/env python3
"""
Скрипт для скачивания шрифтов DejaVu для PDF генерации
"""
import urllib.request
import os
from pathlib import Path

def download_fonts():
    """Скачивает шрифты DejaVu"""
    fonts_dir = Path("assets/fonts")
    fonts_dir.mkdir(parents=True, exist_ok=True)
    
    # URL шрифтов DejaVu (с GitHub)
    fonts = {
        "DejaVuSansCondensed.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSansCondensed.ttf",
        "DejaVuSansCondensed-Bold.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSansCondensed-Bold.ttf",
        "DejaVuSansCondensed-Oblique.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSansCondensed-Oblique.ttf"
    }
    
    for filename, url in fonts.items():
        filepath = fonts_dir / filename
        if filepath.exists():
            print(f"✓ {filename} уже существует")
            continue
            
        try:
            print(f"Скачиваю {filename}...")
            urllib.request.urlretrieve(url, filepath)
            print(f"✓ {filename} скачан успешно")
        except Exception as e:
            print(f"✗ Ошибка при скачивании {filename}: {e}")

if __name__ == "__main__":
    download_fonts()
