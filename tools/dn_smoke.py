# -*- coding: utf-8 -*-
"""
Lightweight smoke tests for DataNewton endpoints available in the current plan.

Usage examples:
  python -m tools.dn_smoke --inn 3801098402
  python -m tools.dn_smoke --ogrn 1026605606620

Reads base URL, token and auth scheme from settings.py.
Prints HTTP status codes and short response previews.
"""
from __future__ import annotations

import sys
import json
import argparse
from typing import Dict, Any, Optional

import httpx

try:
    from settings import (
        DATANEWTON_API,
        DATANEWTON_TOKEN,
        DATANEWTON_AUTH_SCHEME,
    )
except Exception as e:
    print("Failed to import settings:", e)
    sys.exit(1)


def _build_params(inn: Optional[str], ogrn: Optional[str]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if inn:
        params["inn"] = inn
    if ogrn:
        params["ogrn"] = ogrn
    if (DATANEWTON_AUTH_SCHEME or "").lower() == "query" and DATANEWTON_TOKEN:
        params["key"] = DATANEWTON_TOKEN
    return params


def _preview(body_text: str, limit: int = 500) -> str:
    body_text = body_text.strip()
    return body_text[:limit] + ("..." if len(body_text) > limit else "")


def call(client: httpx.Client, path: str, params: Dict[str, Any]) -> None:
    url = DATANEWTON_API.rstrip("/") + path
    try:
        r = client.get(url, params=params)
        print(f"GET {path} -> {r.status_code}")
        try:
            parsed = r.json()
            print(json.dumps(parsed, ensure_ascii=False, indent=2)[:800])
        except Exception:
            print(_preview(r.text))
    except Exception as e:
        print(f"GET {path} -> ERROR: {e}")
    print("-" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test DataNewton endpoints")
    parser.add_argument("--inn", type=str, help="ИНН", default=None)
    parser.add_argument("--ogrn", type=str, help="ОГРН", default=None)
    args = parser.parse_args()

    if not (args.inn or args.ogrn):
        print("Specify --inn or --ogrn")
        return 2

    headers: Dict[str, str] = {"Accept": "application/json"}
    if (DATANEWTON_AUTH_SCHEME or "").lower() != "query" and DATANEWTON_TOKEN:
        # Default to Bearer/X-API-Key via headers
        if (DATANEWTON_AUTH_SCHEME or "").lower() == "x-api-key":
            headers["X-API-Key"] = DATANEWTON_TOKEN
        else:
            headers["Authorization"] = f"Bearer {DATANEWTON_TOKEN}"

    params = _build_params(args.inn, args.ogrn)

    with httpx.Client(timeout=10, headers=headers) as client:
        call(client, "/v1/counterparty", params)
        call(client, "/v1/finance", params)
        call(client, "/v1/paidTaxes", params)
        call(client, "/v1/arbitration-cases", params)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


