# -*- coding: utf-8 -*-
from services.export.gamma_exporter import create_generation

def test_create_generation_payload_building(monkeypatch):
    captured = {}

    class DummyResponse:
        status_code = 200
        def json(self):
            return {"generationId": "gen_123"}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def post(self, url, headers=None, json=None):
            captured['url'] = url
            captured['headers'] = headers
            captured['json'] = json
            return DummyResponse()

    import services.export.gamma_exporter as ge
    monkeypatch.setattr(ge.httpx, 'Client', DummyClient)

    gen_id = create_generation(
        input_text="# Заголовок\n---\nТело",
        export_as="pdf",
        format="document",
        text_mode="preserve",
        language="ru",
        theme_name="classic",
        card_split="inputTextBreaks",
        num_cards=10,
        additional_instructions="сохраняй структуру",
    )
    assert gen_id == "gen_123"
    assert captured['json']['inputText'].startswith('# Заголовок')
    assert captured['json']['exportAs'] == 'pdf'
    assert captured['json']['textOptions']['language'] == 'ru'
    assert captured['json']['format'] == 'document'
    assert captured['json']['cardSplit'] == 'inputTextBreaks'
    assert captured['json']['numCards'] == 10
    assert captured['json']['additionalInstructions'] == 'сохраняй структуру'

