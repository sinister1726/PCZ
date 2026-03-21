# Nexora Cricket Bot

A Telegram bot for cricket-based group games with a Flask web log dashboard.

## Architecture

- **bot.py** - Main Telegram bot entry point using Pyrogram/Pyrofork
- **app.py** - Flask web dashboard for live log monitoring (runs on port 5000)
- **plugins/** - Modular bot plugins (game, admin, common, utilities)
- **database/** - PostgreSQL database layer using asyncpg
- **utils/** - Shared utility functions
- **config.py** - Centralized configuration (API keys, DB URL, bot settings)
- **Assets/** - Static resources (fonts, images for scorecards)

## Technologies

- **Language:** Python 3.12
- **Telegram Framework:** Pyrofork (Pyrogram fork)
- **Database:** PostgreSQL (external Neon hosted) via asyncpg
- **Web Dashboard:** Flask + Gunicorn
- **Image Processing:** Pillow, matplotlib

## Running

The app runs both processes together:
- Gunicorn serves the Flask dashboard on `0.0.0.0:5000`
- `python3 bot.py` runs the Telegram bot

```
gunicorn --bind 0.0.0.0:5000 app:app & python3 bot.py
```

## Deployment

Deployed as a VM (always-running) deployment to keep the Telegram bot alive continuously.

## Configuration

All configuration is in `config.py`:
- `API_ID`, `API_HASH`, `BOT_TOKEN` - Telegram credentials
- `DATABASE_URL` - PostgreSQL connection string (Neon)
- `OWNER_IDS` - Bot owner Telegram user IDs
- `LOG_CHANNEL` - Telegram channel ID for startup logs
