# Lunation - WoW Guild Discord Bot

A simple Discord bot for the Lunation WoW Guild.

## Features

- Auto-assigns Member role to new users
- Posts welcome embed in #willkommen channel

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your bot token:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

3. Invite the bot to your server with the following permissions:
   - Manage Roles
   - Send Messages
   - Read Message History

4. Run the bot:
   ```
   python bot.py
   ```

## Configuration

The bot uses these Discord IDs (configured in bot.py):
- Member Role: 1498403566208028934
- Willkommen Channel: 1498404776650735676
- Rules Channel: 1498405058650312754
- Bewerbung Channel: 1498614623065215007