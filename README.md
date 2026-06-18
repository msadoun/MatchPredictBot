# MatchPredictBot

Arabic Telegram bot for **FIFA World Cup 2026** match predictions, private leaderboards, and group-friendly usage (replies go to the requester’s DM only).

**Repository:** [github.com/msadoun/MatchPredictBot](https://github.com/msadoun/MatchPredictBot)

## Features

- World Cup 2026 fixtures (group stage + knockout rounds) with Arabic team names
- Step-by-step prediction flow: pick match → choose winner/draw → enter score
- Tiered scoring (3 / 2 / 1 points); **draws score only on exact result**
- Leaderboard with rank, name, and points
- **Per-group** predictions and leaderboards (groups don’t mix)
- Inline menu buttons on `/start` (no bottom reply keyboard)
- Works in **private chat** and **groups** (group commands reply in private DM)
- Admin tools to add matches, set results, and reload fixtures

## Quick start

### Requirements

- Python 3.11+ (tested on 3.13)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### Install

```bash
git clone https://github.com/msadoun/MatchPredictBot.git
cd MatchPredictBot
python -m pip install -r requirements.txt
```

### Configure

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=your_token_here
ADMIN_USER_IDS=your_telegram_user_id
DATABASE_PATH=data/bot.db
```

Get your Telegram user ID from [@userinfobot](https://t.me/userinfobot).

### Load World Cup matches

```bash
python seed_worldcup.py
```

### Run the bot

```bash
python main.py
```

Keep the process running (or deploy to a VPS — see [HANDOVER.md](HANDOVER.md)).

## User commands

| Command | Description |
|---------|-------------|
| `/start` | Register and show inline menu buttons |
| `/predict` | Start a prediction |
| `/matches` | Today’s open matches (`/matches 2026-06-18` for a date) |
| `/mypredictions` | Your predictions and points |
| `/leaderboard` or `/lb` | Standings |
| `/cancel` | Cancel in-progress prediction |

## Admin commands

| Command | Description |
|---------|-------------|
| `/addmatch` | Add a custom match |
| `/setresult <id> <home> <away>` | Enter final score and update points |
| `/closematch <id>` | Close predictions without a result |
| `/allmatches` | List all matches |
| `/loadworldcup` | Import fixtures (skips duplicates) |

## Scoring

| Points | Rule |
|--------|------|
| **3** | Exact score |
| **2** | Correct winner + correct winner’s goals (e.g. actual 4-1, predicted 4-0) |
| **1** | Correct winner, wrong goals |
| **0** | Wrong winner, or draw predicted but not exact (e.g. predicted 2-2, actual 1-1) |

## Groups

1. Add **@FTM3naBot** (or your bot username) to the group.
2. Each user must open the bot in **private chat** and send `/start` once.
3. In the group, use e.g. `/predict@YourBotName` — all responses arrive in **private DM** only.
4. Predictions and `/leaderboard` are **scoped to that group** — each group has its own standings.
5. Use `/predict` from inside a group so your picks count toward that group’s leaderboard.

## Project layout

```
MatchPredictBot/
├── main.py              # Entry point, handler registration
├── handlers.py          # Commands and prediction flow
├── database.py          # SQLite schema and queries
├── scoring.py           # Points calculation
├── messages.py          # Arabic UI strings
├── user_messaging.py    # Private DM routing for groups
├── worldcup2026.py      # Fixture data (Arabic)
├── teams_ar.py          # English→Arabic migration map
├── seed_worldcup.py     # One-shot DB seed script
├── config.py            # Environment config
├── test_scoring.py      # Scoring unit checks
├── requirements.txt
├── HANDOVER.md          # Developer handover (read before extending)
└── data/                # SQLite DB (gitignored)
```

## Tests

```bash
python -c "from test_scoring import *; test_exact_score(); test_winning_team_goals(); test_correct_winner_only(); test_correct_draw_only(); test_wrong_prediction(); print('OK')"
```

## Security

- **Never commit** `.env` or bot tokens.
- If a token is leaked, revoke it in BotFather and update `.env`.
- Rotate `ADMIN_USER_IDS` if you change admin accounts.

## Further reading

See **[HANDOVER.md](HANDOVER.md)** for architecture, database schema, deployment options, and a full guide for continuing development.

## License

MIT (or specify your license here).
