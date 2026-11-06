#!/usr/bin/env python3
"""Best-effort public Instagram -> RSS collector. Never fabricates posts."""
import base64
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
ET.register_namespace("media", "http://search.yahoo.com/mrss/")

def now():
    return datetime.now(timezone.utc)

def read_json(filename, fallback):
    try:
        return json.loads((BASE / filename).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback

def save_json(filename, value):
    file = BASE / filename
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def iso(dt):
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt.tzinfo is None else dt.astimezone(timezone.utc).isoformat()

def records(config):
    import instaloader
    loader = instaloader.Instaloader(
        quiet=True, download_pictures=False, download_videos=False,
        download_video_thumbnails=False, download_comments=False,
        save_metadata=False, max_connection_attempts=1)
    errors = []
    authenticated = False
    session = os.getenv("INSTAGRAM_SESSION_BASE64", "").strip()
    username = os.getenv("INSTAGRAM_USERNAME", "").strip()
    if session and username:
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "session"
                path.write_bytes(base64.b64decode(session, validate=True))
                path.chmod(0o600)
                loader.load_session_from_file(username, filename=str(path))
                authenticated = True
        except Exception as exc:
            errors.append("Instagram session failed: " + str(exc)[:180])

    output = []
    user_ids = []
    id_to_name = {}
    seen = set()

    def add_post(post, name, kind):
        shortcode = post.shortcode
        if shortcode in seen:
            return
        seen.add(shortcode)
        output.append({
            "id": "post:" + shortcode,
            "account": name,
            "kind": kind,
            "url": "https://www.instagram.com/" + ("reel" if kind == "reel" else "p") + "/" + shortcode + "/",
            "title": "@" + name + " · " + kind.title(),
            "published": iso(post.date_utc),
            "caption": post.caption or "",
            "thumbnail": getattr(post, "url", "") or "",
        })

    for name in config.get("accounts", []):
        try:
            profile = instaloader.Profile.from_username(loader.context, name)
            if profile.is_private:
                errors.append("@" + name + ": profile is private; skipped")
                continue
            user_ids.append(profile.userid)
            id_to_name[profile.userid] = name
            for index, post in enumerate(profile.get_posts()):
                if index >= config.get("posts_per_account", 8):
                    break
                kind = "reel" if getattr(post, "is_video", False) and getattr(post, "typename", "") == "GraphVideo" else "post"
                add_post(post, name, kind)
            try:
                for index, reel in enumerate(profile.get_reels()):
                    if index >= config.get("reels_per_account", 5):
                        break
                    add_post(reel, name, "reel")
            except Exception as exc:
                errors.append("@" + name + " reels: " + str(exc)[:180])
        except Exception as exc:
            errors.append("@" + name + " posts: " + str(exc)[:180])

    if authenticated and user_ids:
        try:
            for story in loader.get_stories(userids=user_ids):
                name = id_to_name.get(story.owner_id)
                if not name:
                    continue
                for index, item in enumerate(story.get_items()):
                    if index >= config.get("max_stories_per_account", 20):
                        break
                    sid = str(item.mediaid)
                    output.append({
                        "id": "story:" + name + ":" + sid,
                        "account": name,
                        "kind": "story",
                        "url": "https://www.instagram.com/stories/" + name + "/" + sid + "/",
                        "title": "@" + name + " · Story",
                        "published": iso(item.date_utc),
                        "caption": item.caption or "",
                        "thumbnail": getattr(item, "url", "") or "",
                    })
        except Exception as exc:
            errors.append("Stories: " + str(exc)[:180])
    elif not authenticated:
        errors.append("Stories require an authorized Instagram session; no session is configured.")
    return output, errors, authenticated

def merge(old, fresh):
    combined = {item["id"]: item for item in old if isinstance(item, dict) and item.get("id")}
    combined.update({item["id"]: item for item in fresh})
    result = []
    for item in combined.values():
        try:
            published = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
            age = now() - published
            retention = timedelta(hours=48) if item.get("kind") == "story" else timedelta(days=30)
            if timedelta(0) <= age <= retention:
                result.append(item)
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(result, key=lambda item: item["published"], reverse=True)[:250]

def build_feed(items):
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    fields = {
        "title": "Instagram — Onda MX and Galería Alentar",
        "link": "https://www.instagram.com/",
        "description": "Unendorsed monitoring of links to public Instagram posts, reels and stories.",
        "language": "es-MX",
        "lastBuildDate": format_datetime(now()),
    }
    for key, value in fields.items():
        ET.SubElement(channel, key).text = value
    for item in items:
        node = ET.SubElement(channel, "item")
        for key, value in [
            ("title", item["title"]),
            ("link", item["url"]),
            ("guid", item["id"]),
            ("pubDate", format_datetime(datetime.fromisoformat(item["published"]))),
            ("category", item["kind"]),
            ("description", item.get("caption") or "Open original Instagram content."),
        ]:
            ET.SubElement(node, key, {"isPermaLink": "false"} if key == "guid" else {}).text = value
        ET.SubElement(node, "category").text = "@" + item["account"]
        thumbnail = item.get("thumbnail", "")
        if thumbnail.startswith("https://"):
            ET.SubElement(node, "{http://search.yahoo.com/mrss/}thumbnail", {"url": thumbnail})
    ET.ElementTree(rss).write(BASE / "docs/rss.xml", encoding="utf-8", xml_declaration=True)

def main():
    config = read_json("accounts.json", {"accounts": []})
    if not config["accounts"]:
        raise SystemExit("No configured accounts")
    try:
        fetched, errors, authenticated = records(config)
    except Exception as exc:
        fetched, errors, authenticated = [], ["Collector failed: " + str(exc)[:220]], False
    current = merge(read_json("data/items.json", []), fetched)
    save_json("data/items.json", current)
    build_feed(current)
    status = {
        "last_checked_utc": now().isoformat(),
        "received_new_this_check": len(fetched),
        "total_items_in_rss": len(current),
        "session_configured": authenticated,
        "accounts": config["accounts"],
        "errors": errors,
        "note": "An empty feed is not evidence that Instagram was successfully queried; media URLs expire.",
    }
    save_json("docs/status.json", status)
    print(json.dumps(status, ensure_ascii=False))
    for error in errors:
        print("WARNING:", error, file=sys.stderr)

if __name__ == "__main__":
    main()
