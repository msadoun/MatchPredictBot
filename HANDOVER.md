# MatchPredictBot — Developer Handover

This document is a comprehensive guide for anyone continuing development on [MatchPredictBot](https://github.com/msadoun/MatchPredictBot). Read it end-to-end before making changes.

---

## Table of contents

1. [Product summary](#1-product-summary)
2. [Technology stack](#2-technology-stack)
3. [Repository structure](#3-repository-structure)
4. [Runtime architecture](#4-runtime-architecture)
5. [Configuration and secrets](#5-configuration-and-secrets)
6. [Database](#6-database)
7. [Scoring system](#7-scoring-system)
8. [Prediction user flow](#8-prediction-user-flow)
9. [Group vs private chat behavior](#9-group-vs-private-chat-behavior)
10. [World Cup fixtures](#10-world-cup-fixtures)
11. [Arabic localization](#11-arabic-localization)
12. [Admin capabilities](#12-admin-capabilities)
13. [How to run locally](#13-how-to-run-locally)
14. [Deployment for 24/7 uptime](#14-deployment-for-247-uptime)
15. [Common operations](#15-common-operations)
16. [Testing](#16-testing)
17. [Known limitations](#17-known-limitations)
18. [Suggested future work](#18-suggested-future-work)
19. [Troubleshooting](#19-troubleshooting)
20. [Change log (initial release)](#20-change-log-initial-release)

---

## 1. Product summary

**MatchPredictBot** is a Telegram bot that lets participants predict football match scores and compete on a leaderboard. It was built for **FIFA World Cup 2026** but supports arbitrary matches via admin commands.

**Core user stories:**

- User registers via `/start`
- User predicts a match outcome through an interactive flow
- Admin enters real results; points are calculated automatically
- Users view standings on `/leaderboard`
- Group usage does not spam the chat — replies go to the user’s **private DM**

**Bot username (production):** `@FTM3naBot` (hardcoded as `BOT_USERNAME` in `handlers.py` for group help text — update if you rename the bot).

---

## 2. Technology stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | Python 3.11+ | Developed on 3.13 |
| Telegram API | [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) **21.10** | Async polling mode |
| Database | SQLite | File at `data/bot.db` by default |
| Config | `python-dotenv` | `.env` file |
| Hosting | Local / VPS | No cloud config included yet |

**No web server, no Redis, no Docker** — intentionally minimal for easy handover.

---

## 3. Repository structure

```
main.py              # Application entry: builds PTB Application, registers handlers
handlers.py          # All command handlers + prediction callback logic (~700 lines)
database.py          # SQLite access, models, seed/migrate helpers
scoring.py           # Pure function: calculate_points()
messages.py          # All Arabic user-facing strings (single i18n file)
user_messaging.py    # reply_to_user() / edit_or_send_user() for group DM routing
worldcup2026.py      # 104 World Cup fixtures (Arabic names + Arabic group labels)
teams_ar.py          # English→Arabic team name map (used by migrate_team_names_to_arabic)
seed_worldcup.py     # CLI: init_db() + seed_world_cup_matches()
config.py            # Reads TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS, DATABASE_PATH
test_scoring.py      # Informal unit tests for scoring (not pytest)
requirements.txt
.env.example         # Template — copy to .env
.gitignore           # Ignores .env, data/
```

### File responsibilities (detail)

#### `main.py`

- Validates `BOT_TOKEN` exists
- Calls `init_db()`
- Registers all `CommandHandler`, `CallbackQueryHandler`, `MessageHandler` instances
- `post_init`: sets Arabic command menu via `set_my_commands`, clears Web App menu button via `set_chat_menu_button(MenuButtonDefault())`
- `run_polling(allowed_updates=["message", "callback_query"])`

**Handler groups:**

- Group `0`: `stale_keyboard_handler` — ignores legacy reply-keyboard label taps, redirects to `/start`
- Group `1`: `predict_score_message` — free-text score entry during prediction

**Callback handlers:** `menu:` (main inline menu), `pred:` (prediction flow)

#### `handlers.py`

Central orchestration. Key functions:

| Function | Role |
|----------|------|
| `start_command` | Upsert user, show welcome + inline menu buttons |
| `menu_callback` | Inline menu taps (`menu:matches`, `menu:predict`, etc.) |
| `matches_command` | List open matches for a date |
| `predict_command` | Start prediction (match list or direct ID) |
| `predict_callback` | Inline button callbacks (`pred:match:`, `pred:pick:`) |
| `predict_score_message` | Parse `2-1` style input, save prediction |
| `leaderboard_command` | Format and send standings (group-scoped in groups) |
| `group_welcome` | One message when bot joins a group |
| Admin commands | `addmatch`, `setresult`, `closematch`, `allmatches`, `loadworldcup` |

#### `database.py`

- Context manager `get_db()` — auto commit/rollback
- CRUD for users, matches, predictions
- `register_group_member()` — tracks which users used the bot in each group
- `get_leaderboard(group_chat_id=...)` — filters by `predictions.chat_id` (0 = private)
- `save_prediction(..., group_chat_id=0)` — predictions are per group or private
- `set_match_result()` — updates match + recalculates all prediction points for that match
- `seed_world_cup_matches()` — idempotent insert from `worldcup2026.py`
- `migrate_team_names_to_arabic()` — one-time EN→AR rename in existing rows

#### `user_messaging.py`

**Critical for groups.** All user-facing replies should go through:

- `reply_to_user()` — private chat: normal reply (strips legacy reply keyboard); group: `send_message(user.id, ...)`
- `edit_or_send_user()` — callback edits in private; in group sends DM and deletes/minimizes group message

If the user never `/start`ed in private, Telegram returns `Forbidden` — bot shows `DM_REQUIRED` in the group.

---

## 4. Runtime architecture

```
Telegram servers
       │ long polling (getUpdates)
       ▼
   main.py  ──►  handlers.py  ──►  database.py  ──►  data/bot.db
                    │                    ▲
                    ├── scoring.py       │
                    ├── messages.py      │
                    └── user_messaging.py
```

**Data flow when admin sets a result:**

1. `/setresult 22 2 1`
2. `set_match_result()` writes `home_score`, `away_score`, sets `is_open=0`
3. For each prediction on match 22, `calculate_points()` runs
4. `predictions.points` updated
5. `/leaderboard` reflects new totals via `SUM(points)`

**User identity:**

- Telegram `user.id` stored in `users.telegram_id`
- Internal `users.id` used as FK in `predictions`

---

## 5. Configuration and secrets

### Environment variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | From [@BotFather](https://t.me/BotFather) |
| `ADMIN_USER_IDS` | Yes | Comma-separated Telegram numeric user IDs |
| `DATABASE_PATH` | No | Default `data/bot.db` |

### Security checklist

- [ ] `.env` is in `.gitignore` — **never push tokens**
- [ ] Revoke token in BotFather if exposed in chat/logs
- [ ] `ADMIN_USER_IDS` should only list trusted operators
- [ ] SQLite file contains user data — back up `data/bot.db` regularly

### Getting admin user ID

Message [@userinfobot](https://t.me/userinfobot) or inspect bot logs when you send `/start`.

---

## 6. Database

### Schema

**`users`**

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Internal ID |
| telegram_id | INTEGER UNIQUE | Telegram user ID |
| username | TEXT | Nullable |
| display_name | TEXT | full_name fallback |
| joined_at | TEXT ISO | UTC |

**`matches`**

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Used in `/predict` and buttons |
| home_team | TEXT | Arabic in production data |
| away_team | TEXT | |
| kickoff_at | TEXT | Format: `2026-06-17 · المجموعة ل` |
| home_score | INTEGER | NULL until result set |
| away_score | INTEGER | NULL until result set |
| is_open | INTEGER | 1 = predictions allowed |
| created_at | TEXT ISO | |

**`predictions`**

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | INTEGER FK → users | |
| match_id | INTEGER FK → matches | |
| chat_id | INTEGER | `0` = private; Telegram group chat ID otherwise |
| home_score | INTEGER | User’s predicted home goals |
| away_score | INTEGER | User’s predicted away goals |
| points | INTEGER | NULL until match has result |
| created_at / updated_at | TEXT | Upsert on re-prediction |

**`group_members`**

| Column | Type | Notes |
|--------|------|-------|
| chat_id | INTEGER | Telegram group chat ID |
| user_id | INTEGER FK → users | |
| joined_at | TEXT ISO | Set when user uses bot from that group |

**Unique constraint:** `(user_id, match_id, chat_id)` — one prediction per user per match per group (overwritable).

### Opening the database

```bash
sqlite3 data/bot.db
.tables
SELECT * FROM matches WHERE is_open = 1 LIMIT 5;
SELECT u.display_name, SUM(p.points) FROM users u
  JOIN predictions p ON p.user_id = u.id
  WHERE p.chat_id = 0
  GROUP BY u.id ORDER BY 2 DESC;
```

### Backup

```bash
copy data\bot.db data\bot.db.backup
```

---

## 7. Scoring system

Implemented in `scoring.py` → `calculate_points(predicted_home, predicted_away, actual_home, actual_away)`.

| Points | Condition |
|--------|-----------|
| 3 | Exact score |
| 2 | Correct winner **and** predicted winner’s goal count matches actual |
| 1 | Correct winner only |
| 0 | Wrong winner, or draw without exact score |

**Examples:**

| Actual | Predicted | Points | Reason |
|--------|-----------|--------|--------|
| 4-1 | 4-1 | 3 | Exact |
| 4-1 | 4-0 | 2 | Winner + winner goals (4) |
| 4-1 | 3-0 | 1 | Winner only |
| 4-1 | 1-4 | 0 | Wrong winner |
| 1-1 | 0-0 | 0 | Draw but not exact |
| 1-1 | 1-1 | 3 | Exact draw |

**Draw handling:** Draws award points **only** for an exact score. The 2-point and 1-point tiers apply to winner predictions only.

**Changing rules:** Edit `scoring.py`, then re-run point recalculation for finished matches (not automated — add a script or call `set_match_result` again with same scores).

---

## 8. Prediction user flow

### Private chat

1. `/predict` → inline list of today’s open matches
2. Tap match → “من سيفوز؟” with home / تعادل / away buttons
3. Tap winner → prompt to type score `2-1`
4. User sends `2-1` → `_scores_from_pick()` maps higher number to chosen winner
5. Saved via `save_prediction()`

**Score input rules (`_scores_from_pick`):**

- User types two numbers separated by `-`
- For a **winner** pick: higher number assigned to that side (so `1-4` with home winner → 4-1)
- For **draw**: both numbers must be equal; equal scores (e.g. `0-0`) are always saved as a draw
- `prediction_group_chat_id` in `user_data` links the pick to the group where `/predict` was started

### Direct match ID

```
/predict 22
```

Skips match list, goes straight to winner selection for match #22.

### State in `context.user_data`

| Key | When set |
|-----|----------|
| `prediction_step` | `"entering_score"` after winner chosen |
| `prediction_match_id` | Match ID |
| `prediction_pick` | `"home"` / `"away"` / `"draw"` |
| `prediction_home_team` / `prediction_away_team` | Cached names for confirmation message |
| `prediction_group_chat_id` | Group chat ID (`0` if started in private) |

Cleared by `_clear_prediction_state()` on save or `/cancel`.

### Callback data format

| Pattern | Meaning |
|---------|---------|
| `pred:match:{id}` | User selected match from list |
| `pred:pick:{id}:home` | User picked home win |
| `pred:pick:{id}:away` | Away win |
| `pred:pick:{id}:draw` | Draw |

**Max 64 bytes** — current patterns are safe.

---

## 9. Group vs private chat behavior

| Aspect | Private | Group |
|--------|---------|-------|
| Main menu | Inline buttons on `/start` | N/A (use commands or DM after `/start`) |
| Command responses | In chat | **DM to user** |
| Inline buttons | In chat | DM to user (group message deleted/minimized) |
| Score text input | In chat | **Private only** (`predict_score_message` returns early in groups) |
| Leaderboard / predictions | `chat_id = 0` | Scoped to that group’s `chat_id` |
| Welcome on bot add | N/A | One `GROUP_WELCOME` message in group |

**Prerequisite:** User must `/start` the bot in private once so Telegram allows the bot to DM them.

**Legacy reply keyboard:** Old bottom menus (توقع، المباريات، …) are removed. `/start` sends `ReplyKeyboardRemove`. If a Web App icon persists, check BotFather → Bot Settings → Menu Button.

---

## 10. World Cup fixtures

- **Source:** FIFA World Cup 2026 schedule (group stage + knockout)
- **File:** `worldcup2026.py` — 104 fixtures, Arabic team names
- **Seed:** `python seed_worldcup.py` or admin `/loadworldcup`
- **Idempotency:** Skips matches where `(home_team, away_team, kickoff_at)` already exists
- **Auto-close:** Matches with `kickoff_at` date before seed time get `is_open=0`

### Kickoff label format

```
2026-06-17 · المجموعة ل
```

`kickoff_deadline()` in `worldcup2026.py` treats date-only labels as open until `23:59` on that day (UTC).

### Migrating English → Arabic names

If DB was seeded with English names:

```python
from database import init_db, migrate_team_names_to_arabic
init_db()
print(migrate_team_names_to_arabic())  # {'updated': N}
```

Mapping lives in `teams_ar.py`.

---

## 11. Arabic localization

All UI strings are in **`messages.py`** (no gettext / i18n framework).

To add English or bilingual support:

1. Create `messages_en.py` or a dict-based locale selector
2. Replace `import messages as msg` with a resolver based on user preference
3. Update `main.py` `set_my_commands` per locale

**Team names** are data (in DB), not in `messages.py`.

**Inline menu callback data** uses the `menu:` prefix; prediction callbacks use `pred:`.

---

## 12. Admin capabilities

Admins are defined only by `ADMIN_USER_IDS` in `.env` — no DB roles table.

| Command | Example |
|---------|---------|
| Add match | `/addmatch إنجلترا كرواتيا 2026-06-17` |
| Set result | `/setresult 22 2 1` |
| Close without result | `/closematch 22` |
| List all | `/allmatches` |
| Reload WC fixtures | `/loadworldcup` |

Admin replies in groups also go to **private DM** (same as users).

---

## 13. How to run locally

```bash
cd MatchPredictBot
python -m pip install -r requirements.txt
copy .env.example .env
# Edit .env
python seed_worldcup.py
python main.py
```

**Windows:** Keep terminal open. `Ctrl+C` stops the bot.

**Multiple instances:** Do not run two processes with the same token — Telegram returns `409 Conflict`.

---

## 14. Deployment for 24/7 uptime

The bot uses **long polling** — the Python process must stay alive.

### Option A: Linux VPS (recommended)

```bash
# On Ubuntu
sudo apt update && sudo apt install python3 python3-pip python3-venv
git clone https://github.com/msadoun/MatchPredictBot.git
cd MatchPredictBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
python seed_worldcup.py
```

**systemd unit** `/etc/systemd/system/matchpredictbot.service`:

```ini
[Unit]
Description=MatchPredictBot Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/MatchPredictBot
EnvironmentFile=/home/ubuntu/MatchPredictBot/.env
ExecStart=/home/ubuntu/MatchPredictBot/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now matchpredictbot
sudo journalctl -u matchpredictbot -f
```

### Option B: Railway / Render / Fly.io

- Set env vars in dashboard
- Start command: `python main.py`
- Mount persistent volume for `data/bot.db` (otherwise DB resets on redeploy)

### Option C: Webhook mode (not implemented)

For high scale, migrate from polling to webhook + HTTPS endpoint. Would require refactoring `main.py`.

---

## 15. Common operations

### Add a new match manually

```
/addmatch الفريق_أ الفريق_ب 2026-07-01 · ودية
```

### Enter result after a game

```
/setresult 22 2 1
```

### Re-seed World Cup (safe)

```
/loadworldcup
```

### Reset database completely

```bash
# Stop bot first
del data\bot.db
python seed_worldcup.py
```

### Change bot username reference

Update `BOT_USERNAME = "..."` in `handlers.py` (group welcome + DM error messages).

---

## 16. Testing

### Scoring

```bash
python -c "from test_scoring import *; test_exact_score(); test_winning_team_goals(); test_correct_winner_only(); test_correct_draw_only(); test_wrong_prediction(); print('OK')"
```

### Manual Telegram test checklist

- [ ] `/start` in private — inline menu buttons appear (no bottom keyboard)
- [ ] `/predict` — full flow saves prediction
- [ ] `/mypredictions` shows pick
- [ ] Admin `/setresult` — points appear on `/leaderboard`
- [ ] Two groups — separate leaderboards after `/predict` from each group
- [ ] Add bot to test group — `/predict@Bot` — response in DM only
- [ ] User who never `/start`ed — sees DM_REQUIRED in group

### Recommended additions (not yet done)

- `pytest` suite for `scoring.py` and `database.py`
- CI on GitHub Actions (`pip install`, run tests)

---

## 17. Known limitations

1. **Single SQLite file** — not ideal for high concurrency; fine for small/medium groups.
2. **No prediction deadline enforcement** beyond `is_open` and seed-time date logic — no kickoff-hour auto-lock cron.
3. **Knockout placeholders** (e.g. “فائز م٧٤”) are symbolic until real teams are known.
4. **`user_data` is in-memory** — lost on bot restart mid-prediction (user restarts flow).
5. **No multi-tournament support** — everything is one flat match list.
6. **Per-group scope** — users must run `/predict` from a group for picks to count there; private picks use `chat_id = 0`.
7. **Admin IDs in env only** — no in-bot admin management.

---

## 18. Suggested future work

Prioritized ideas for the next developer:

### High value

- [ ] **Auto-lock predictions** at kickoff (scheduler or check on each `/predict`)
- [ ] **Persistent conversation state** (PTB `PicklePersistence`) so prediction flow survives restarts
- [ ] **Deploy + volume** documentation with Railway/Render one-click
- [ ] **Recalculate all points** admin command after scoring rule changes
- [ ] **Update knockout fixtures** with real teams when groups finish

### UX

- [ ] Reminder notifications before kickoff (needs job queue / APScheduler)
- [ ] `/today` shortcut command
- [ ] Pagination for `/matches` when many games on one day
- [ ] Show prediction count and rank in `/start` greeting

### Technical

- [ ] Extract `handlers.py` into package (`handlers/`, `admin.py`, `predict.py`)
- [ ] Proper `pytest` + GitHub Actions CI
- [ ] Webhook deployment option
- [ ] PostgreSQL for production multi-instance
- [ ] English locale via `messages_en.py`

### Data

- [ ] Pull live results from an API and auto `/setresult`
- [ ] Sync fixtures from FIFA API instead of static `worldcup2026.py`

---

## 19. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `409 Conflict` in logs | Two bot instances polling | Kill all `python main.py` processes |
| Bot silent in group | Privacy mode + non-command message | Use `/command@BotName` |
| “افتح محادثة خاصة…” | User never `/start`ed in DM | User opens bot privately, `/start` |
| Empty leaderboard | No results entered yet | Admin `/setresult` for played matches |
| Wrong points | Scoring rules changed | Re-run `set_match_result` or add recalc script |
| `TELEGRAM_BOT_TOKEN is not set` | Missing `.env` | Copy `.env.example` → `.env` |
| Garbled Arabic in Windows terminal | Console encoding | Use UTF-8 terminal; Telegram UI is fine |

---

## 20. Change log (initial release)

- World Cup 2026: 104 fixtures, Arabic team names
- Prediction flow: inline keyboards + score entry
- Scoring: 3 / 2 / 1 point tiers
- Leaderboard with medals and user rank
- Group support with private DM replies
- Full Arabic UI (`messages.py`)
- Admin match/result management
- SQLite persistence

---

## Contact / ownership

- **GitHub:** [msadoun/MatchPredictBot](https://github.com/msadoun/MatchPredictBot)
- **Original workspace path:** `musab/` (local dev folder name)

When in doubt, start from `main.py` → trace the command you care about in `handlers.py` → follow into `database.py`.

Good luck with the next phase.
