WELCOME = (
    "🎧 *YouTube → Podcast*\n\n"
    "Send me a YouTube link and I'll create an RSS feed you can add to any podcast app "
    "(Apple Podcasts, Pocket Casts, AntennaPod, etc.).\n\n"
    "Supported:\n"
    "• Single video\n"
    "• Playlist\n"
    "• Channel (`@name` or `/channel/…`)\n\n"
    "Commands:\n"
    "/feeds — your RSS feeds\n"
    "/refresh `<feed-id>` — sync new episodes\n"
    "/delete `<feed-id>` — remove a feed\n"
    "/help — show this message"
)

HELP = WELCOME

PROCESSING = "⏳ Fetching YouTube metadata…"

FEED_CREATED = (
    "✅ *{title}*\n"
    "Type: {source_type} · Episodes: {count}\n\n"
    "Add this URL in your podcast app:\n"
    "`{feed_url}`\n\n"
    "Feed ID: `{feed_id}`\n"
    "Use /refresh `{feed_id}` to pull new videos later."
)

FEED_LIST_EMPTY = "You have no feeds yet. Send a YouTube URL to create one."

FEED_LIST_HEADER = "📻 *Your podcast feeds:*\n\n"

FEED_LIST_ITEM = (
    "• *{title}* ({count} episodes)\n"
    "  `{feed_url}`\n"
    "  ID: `{feed_id}`\n\n"
)

FEED_DELETED = "🗑 Feed deleted."

FEED_NOT_FOUND = "Feed not found or you don't own it."

REFRESHING = "🔄 Refreshing feed…"

REFRESH_DONE = "✅ Updated *{title}* — {count} episode(s) in feed."

INVALID_URL = (
    "That doesn't look like a YouTube link.\n\n"
    "Examples:\n"
    "• https://youtube.com/watch?v=…\n"
    "• https://youtube.com/playlist?list=…\n"
    "• https://youtube.com/@channelname"
)

EXTRACTION_FAILED = "❌ Could not read that YouTube URL. Check the link and try again."

DELETE_USAGE = "Usage: /delete `<feed-id>`\nUse /feeds to see your feed IDs."

REFRESH_USAGE = "Usage: /refresh `<feed-id>`\nUse /feeds to see your feed IDs."
