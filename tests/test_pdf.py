#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import pytest

from domain.models import CompanyFull
from reports.pdf import generate_pdf


FONTS_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"


def _fonts_available() -> bool:
    return (FONTS_DIR / "DejaVuSansCondensed.ttf").exists() and (
        FONTS_DIR / "DejaVuSansCondensed-Bold.ttf"
    ).exists()


@pytest.mark.xfail(condition=not _fonts_available(), reason="DejaVu fonts are missing; PDF falls back to text")
def test_generate_pdf_free_with_cyrillic(caplog):
    caplog.set_level("DEBUG")

    company = CompanyFull(
        short_name="ООО \"ЦСО\"",
        full_name="Общество с ограниченной ответственностью \"Центр сервисного обслуживания\"",
        inn="3812150012",
        ogrn="1133850031424",
        kpp="381201001",
        status="Действующее",
        reg_date="15.01.2013",
        address="664000, г. Иркутск, ул. Ленина, д. 1",
        director="Иванов Иван Иванович",
        source_url="/test",
    )

    pdf_bytes = generate_pdf(company, "free")

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 100

    # В логах не должно быть Unicode-исключений
    combined = "\n".join(
        f"{rec.levelname}: {rec.getMessage()}" for rec in caplog.records
    )
    assert "FPDFUnicodeEncodingException" not in combined
    assert "Unicode font not available" not in combined


