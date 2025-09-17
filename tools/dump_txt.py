# -*- coding: utf-8 -*-
import asyncio
import sys
from pathlib import Path
from scraping.client import ThrottledClient
from scraping.multipage_txt import fetch_all_texts
from services.text_dump import build_txt

USAGE = (
    "Usage: python tools/dump_txt.py <rusprofile_url_or_id> [output.txt]\n"
    "Example: python tools/dump_txt.py https://www.rusprofile.ru/id/799957 out.txt\n"
)


def normalize_input(arg: str) -> str:
    if arg.startswith("http"):
        return arg
    return f"https://www.rusprofile.ru/id/{arg.strip()}"


async def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)
    url = normalize_input(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else "company_dump.txt"

    client = ThrottledClient()
    try:
        bundle = await fetch_all_texts(url, client, include_main=True)
    finally:
        await client.close()

    text = build_txt(bundle, source_url=url)
    Path(out).write_text(text, encoding="utf-8")
    print(f"Saved: {Path(out).resolve()} ({len(text.encode('utf-8'))} bytes)")


if __name__ == "__main__":
    asyncio.run(main())


