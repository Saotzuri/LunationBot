# Lunation - WoW Guild Discord Bot

A Discord bot for the Lunation WoW Guild.

## Features

- Auto-assigns Member role to new users
- Posts welcome embed in #willkommen channel
- Bewerbungs-System mit Modal für Bewerbungen
- Annehmen/Ablehnen Buttons für Offiziere
- Trial-Rolle wird bei Annahme vergeben
- DM-Benachrichtigung an Bewerber bei Annehmen/Ablehnen
- Transcripts werden in #bewerbungs-transcripts gepostet

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
   - Create Channels (für private Bewerbungs-Channels)

4. Run the bot:
   ```
   python bot.py
   ```

## Bot-Befehle

- `/bewerbung-setup` - Postet den Bewerbungs-Embed mit Button (nur Admin)

## Configuration

The bot uses these Discord IDs (configured in bot.py):
- Member Role: 1498403566208028934
- Trial Role: 1498403894857044040
- Offizier Role: 1498401628347437197
- Willkommen Channel: 1498404776650735676
- Rules Channel: 1498405058650312754
- Bewerbung Channel: 1498614623065215007
- Bewerbung Kategorie: 1498612750073462784
- Offizier Ping Channel: 1499744209798955049
- Transcripts Channel: 1499747813070737518