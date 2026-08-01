# FF Guest Account Generator Bot

A Telegram bot that generates Free Fire guest accounts on demand. Uses Tor for IP rotation and supports multiple regions.

## Commands
- `/gen <region> <total> <threads>` – start generating accounts.
- `/status` – check progress.
- `/stop` – cancel generation.
- `/download` – get the accounts file.

## Deployment
- Set `TELEGRAM_BOT_TOKEN` environment variable.
- Deploy on Render with the included `staypresent` keep‑alive.
