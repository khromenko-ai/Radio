#!/usr/bin/env python3
"""Read Instagram public profile pages with a real Chromium browser (Playwright).
Does not access private content, login, or take actions on Instagram.
"""
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from playwright.sync_api import sync_playwright
from collect import now, iso, read_json, save_json, merge, build_feed

BASE = Path(__file__).resolve().parent
BASE_URL = "https://www.instagram.com/"

def capture(page, name, max_count=12):
    """Extract only links actually present in the rendered public profile."""
    links = page.locator('a[href*="/p/"],a[href*="/reel/"]')
    found = []
    observed = set()
    for i in range(min(links.count(), max_count * 3)):
        a = links.nth(i)
        url = a.get_attribute("href") or ""
        match = re.search(r"/(p|reel)/([A-Za-z0-9_-]+)/?", url)
        if not match:
            continue
        typ, shortcode = match.groups()
        if shortcode in observed:
            continue
        observed.add(shortcode)
        img = a.locator("img").first
        desc = ""
        thumb = ""
        try:
            if img.count():
                desc = img.get_attribute("alt") or ""
                thumb = img.get_attribute("src") or ""
        except Exception:
            pass
        found.append({
            "id": "post:" + shortcode,
            "account": name,
            "kind": "reel" if typ == "reel" else "post",
            "url": urljoin(BASE_URL, match.group(0).lstrip("/")),
            "title": "@" + name + " · " + ("Reel" if typ == "reel" else "Post"),
            "published": iso(now()),
            "caption": desc,
            "thumbnail": thumb if thumb.startswith("https://") else "",
        })
        if len(found) >= max_count:
            break
    return found

def main():
    config = read_json("accounts.json", {"accounts": []})
    status = {"checked_utc": now().isoformat(), "engine": "chromium/playwright", "accounts": {}, "retrieved_count": 0}
    result = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-MX", timezone_id="America/Mexico_City",
            viewport={"width": 1280, "height": 900},
        )
        for name in config.get("accounts", []):
            page = context.new_page()
            entry = {"url": BASE_URL + name + "/", "items": 0}
            try:
                response = page.goto(entry["url"], wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(3500)
                entry["http_status"] = response.status if response else None
                entry["final_url"] = page.url
                entry["page_title"] = page.title()[:150]
                got = capture(page, name)
                if got:
                    result.extend(got)
                    entry["items"] = len(got)
                else:
                    entry["error"] = "No visible public post links in Chromium DOM (login wall, block, or empty profile)"
            except Exception as exc:
                entry["error"] = str(exc)[:300]
            finally:
                status["accounts"][name] = entry
                page.close()
        browser.close()
    status["retrieved_count"] = len(result)
    old = read_json("data/items.json", [])
    merged = merge(old, result)
    save_json("data/items.json", merged)
    build_feed(merged)
    save_json("docs/browser_status.json", status)
    print(json.dumps(status, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
