# Microsoft Teams EID Schedule Bot

Bot that replies to **`/date`** with today's EID opening hours for Abu Dhabi, Sharjah, Ajman, and Dubai (Asia/Dubai time).

## Example reply

```
Abu Dhabi
EID// Tuesday , 15 September, 2026 // 4:00 PM to 9:30 PM

Sharjah
EID// Tuesday , 15 September, 2026 //  PM to 9:30 PM

Ajman
EID// Tuesday , 15 September, 2026 // 3:00 PM to 9:30 PM

Dubai
EID// Tuesday , 15 September, 2026 // 2:30 PM to 6:00 PM

EID// Tuesday , 15 September, 2026 // 6:00 PM to 9:30 PM
```

## Requirements

- Python 3.11+
- An Azure Bot resource (App ID + password/secret)
- Microsoft Teams app package (see `manifests/`)

## Setup

```bash
cd teams_bot
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
MicrosoftAppId=your-azure-bot-app-id
MicrosoftAppPassword=your-azure-bot-client-secret
MicrosoftAppTenantId=your-tenant-id
MicrosoftAppType=SingleTenant
PORT=3978
BOT_TIMEZONE=Asia/Dubai
```

## Run locally

```bash
python main.py
```

The bot listens on `http://0.0.0.0:3978/api/messages`.

### Test with Bot Framework Emulator

1. Start the bot (`python main.py`).
2. Open [Bot Framework Emulator](https://github.com/Microsoft/BotFramework-Emulator).
3. Connect to `http://localhost:3978/api/messages` (leave App ID/password empty for local anonymous testing).
4. Send `/date`.

### Expose for Teams (ngrok)

```bash
ngrok http 3978
```

Set the Azure Bot messaging endpoint to:

`https://<your-ngrok-subdomain>.ngrok-free.app/api/messages`

## Deploy to Teams

1. Create an **Azure Bot** (Single Tenant) and note App ID / secret / tenant.
2. Set the messaging endpoint to your public HTTPS URL + `/api/messages`.
3. Enable the **Microsoft Teams** channel on the Azure Bot.
4. Edit `manifests/manifest.json`: replace `YOUR_BOT_APP_ID` with the App ID.
5. Zip `manifests/manifest.json` with color/outline icons (add `color.png` 192×192 and `outline.png` 32×32).
6. In Teams → Apps → Manage your apps → Upload a custom app → select the zip.

## Commands

| Command | Description |
|---------|-------------|
| `/date` | Today's EID hours per emirate |
| `/help` | Short help text |

## Tests

```bash
cd teams_bot
python -m pytest test_messages.py -q
```
