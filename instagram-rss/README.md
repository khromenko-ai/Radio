# Instagram RSS — @onda_mx and @galeriaalentar

This is an isolated free monitor in the existing public Radio repository. It does not alter the Radio app.

- **RSS feed:** https://raw.githubusercontent.com/khromenko-ai/Radio/main/instagram-rss/docs/rss.xml
- **Latest status and errors:** https://raw.githubusercontent.com/khromenko-ai/Radio/main/instagram-rss/docs/status.json
- **Workflow:** https://github.com/khromenko-ai/Radio/actions/workflows/instagram-rss.yml
- **Frequency:** every four hours (GitHub Actions), plus push/manual run.

## Current result

The first successful GitHub Actions job ran on **2026-11-06 09:07 UTC** and refreshed status.json. Instagram responded HTTP 302 for both public profiles, so **zero posts have been retrieved**. The feed exists but is currently empty. Never interpret an empty feed as evidence that no posts or stories were published.

## Stories

Instaloader needs an authorized Instagram session for Stories. The optional workflow secrets are `INSTAGRAM_USERNAME` and `INSTAGRAM_SESSION_BASE64` (base64 of a valid Instaloader session file). This connection has **not** been configured. No Instagram passwords or cookies are stored in the public repository. If an Instagram session is connected later, story availability still cannot be guaranteed.

## How it works

The `instagram-rss/collect.py` script uses Instaloader for public posts and reels, with optional authenticated Stories. It writes:
- `docs/rss.xml`: RSS 2.0 feed with source links and captions if available.
- `docs/status.json`: last check and detailed retrieval errors.
- `data/items.json`: deduplicated metadata; stories retained up to 48h, other entries up to 30 days.

Temporary Instagram CDN image links might expire. This tool links to originals; it does not mirror or re-publish third-party media.

## Limits

- Public GitHub Actions is free subject to platform policies and quotas.
- Instagram rate limits or authentication challenges can prevent retrieval.
- A public RSS URL alone does not automatically subscribe an external agent. Wabi must ingest the URL, and ChatGPT can read it when given URL access.
- Work and Codex are not required.
