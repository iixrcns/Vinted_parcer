# Telegram Vinted Bot

A Telegram bot that allows users to search listings on Vinted using an interactive menu with inline buttons. Users can configure filters such as price range, clothing category, and keywords, then receive matching items directly in Telegram.


## Disclaimer

This project is intended for educational purposes.

Users are responsible for ensuring that their use of this software complies with Vinted's Terms of Service and applicable laws.

This project is not affiliated with, endorsed by, or associated with Vinted.

## Features

* Search Vinted listings directly from Telegram
* Filter by:

  * Price range
  * Clothing category
  * Custom keywords
* User-friendly inline button interface
* Automatic retrieval of matching items from the Vinted API

## Requirements

* Python 3.10+
* Telegram Bot Token

## Installation

### 1. Clone the repository

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a Telegram Bot

Create a new bot using [BotFather](https://t.me/BotFather) and obtain your bot token.

### 4. Configure environment variables

Linux/macOS:

```bash
export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
```

Windows (PowerShell):

```powershell
$env:TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
```

> **Important:** Never commit your bot token to GitHub. Use environment variables or a `.env` file that is excluded from version control.

## Running the Bot

```bash
python bot.py
```

The bot uses long polling to receive updates from Telegram.

## Usage

1. Open your bot in Telegram.
2. Send the `/start` command.
3. Select the desired filters using the inline buttons.
4. Receive matching Vinted listings directly in the chat.
5. Copy vinted_cookies.example.py to vinted_cookies.py
6. Fill in your own cookies.


