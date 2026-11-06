# Instagram RSS monitoring

Isolated feed collector for public Instagram accounts @onda_mx and @galeriaalentar. This directory does not modify the Radio application.

Feed (when populated): https://raw.githubusercontent.com/khromenko-ai/Radio/main/instagram-rss/rss.xml
Status: https://raw.githubusercontent.com/khromenko-ai/Radio/main/instagram-rss/status.json

Refresh: GitHub Actions scheduled every 4 hours. Stories require an Instagram login session; anonymous Instagram extraction is not reliable. If a query is blocked, status.json records the error rather than inventing items.

No private account content, credentials, or session files should be committed to this public repository.
