# YouTube → Podcast Telegram Bot

Turn YouTube **videos**, **playlists**, and **channels** into podcast RSS feeds you can subscribe to in Apple Podcasts, Pocket Casts, AntennaPod, and other podcast apps.

## How it works

1. Send a YouTube URL to the Telegram bot.
2. The bot extracts metadata with [yt-dlp](https://github.com/yt-dlp/yt-dlp) and stores it in SQLite.
3. You get a public RSS feed URL like `https://your-host/feed/<uuid>.xml`.
4. Your podcast app fetches episodes; audio is resolved on demand via a redirect to YouTube's stream.

## Requirements

- Python 3.11+
- A Telegram bot token ([@BotFather](https://t.me/BotFather))
- A **public HTTPS URL** (`BASE_URL`) — podcast apps must reach your RSS server

## Quick start

```bash
cd podcast_bot
python -m pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

Edit `.env`:

```env
PODCAST_BOT_TOKEN=your_token
BASE_URL=https://your-public-url.example
PORT=8080
```

### Local development with ngrok

Podcast apps need a public URL. Expose the web server:

```bash
# Terminal 1
python main.py

# Terminal 2
ngrok http 8080
```

Set `BASE_URL` in `.env` to the ngrok HTTPS URL (e.g. `https://abc123.ngrok-free.app`), then restart the bot.

## Usage

| Action | How |
|--------|-----|
| Create feed | Send any YouTube video, playlist, or channel URL |
| List feeds | `/feeds` |
| Sync new videos | `/refresh <feed-id>` |
| Delete feed | `/delete <feed-id>` |

### Example URLs

- Video: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- Playlist: `https://www.youtube.com/playlist?list=PL…`
- Channel: `https://www.youtube.com/@channelname`

## Deploy on Railway

1. Create a new Railway service pointing at the `podcast_bot` folder.
2. Set environment variables: `PODCAST_BOT_TOKEN`, `BASE_URL` (your Railway public URL), `PORT` (Railway sets this automatically).
3. Add a volume mounted at `/app/data` for persistent SQLite storage.
4. Start command: `python main.py`

## Architecture

```
Telegram bot (polling)  ──►  SQLite (feeds + episodes)
                                    ▲
HTTP server (aiohttp)  ─────────────┘
  GET /feed/{id}.xml   → RSS 2.0 + iTunes tags
  GET /audio/{id}      → 302 redirect to YouTube audio stream
```

## Limitations

- **YouTube ToS**: Streaming via third-party tools may violate YouTube's terms; use for personal listening.
- **Stream URLs expire**: Audio links are resolved fresh on each request; some podcast apps cache aggressively.
- **Episode cap**: Playlists/channels default to the latest 50 videos (`MAX_EPISODES`).
- **No downloads**: Audio is streamed from YouTube, not stored on disk.

## Project layout

```
podcast_bot/
  main.py              # Entry point (bot + web server)
  handlers.py          # Telegram commands
  youtube_extractor.py # yt-dlp wrapper
  rss.py               # RSS feed builder
  web_server.py        # aiohttp routes
  database.py          # SQLite persistence
  config.py            # Environment config
```
