import os
import logging
import asyncio
import requests

logger = logging.getLogger("lunation-bot")

WOWAUDIT_API_KEY = os.getenv("WOWAUDIT_TOKEN")
WOWAUDIT_API_URL = os.getenv("WOWAUDIT_API_URL", "https://www.wowaudit.com")


async def getCharactersWithDiscordIds():
    def _fetch():
        headers = {'accept': 'application/json', 'Authorization': WOWAUDIT_API_KEY}
        characters_url = f'{WOWAUDIT_API_URL}/v1/characters'

        try:
            response = requests.get(characters_url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Fehler beim Laden der Charaktere: {response.status_code}")
                return []

            characters = response.json()
            return [c for c in characters if c.get("note")]
        except Exception as e:
            logger.error(f"Fehler in getCharactersWithDiscordIds: {e}")
            return []

    return await asyncio.to_thread(_fetch)


async def getNextRaid():
    def _fetch():
        headers = {'accept': 'application/json', 'Authorization': WOWAUDIT_API_KEY}
        raids_url = f'{WOWAUDIT_API_URL}/v1/raids?include_past=false'

        try:
            response = requests.get(raids_url, headers=headers)
            if response.status_code != 200:
                return None

            raids = response.json().get("raids", [])
            if not raids:
                return None
            return raids[0]
        except Exception as e:
            logger.error(f"Fehler in getNextRaid: {e}")
            return None

    return await asyncio.to_thread(_fetch)


async def getUnknownSignups(raid_id):
    def _fetch():
        headers = {'accept': 'application/json', 'Authorization': WOWAUDIT_API_KEY}
        details_url = f'{WOWAUDIT_API_URL}/v1/raids/{raid_id}'

        try:
            response = requests.get(details_url, headers=headers)
            if response.status_code != 200:
                return []

            signups = response.json().get("signups", [])
            return [s["character"]["name"] for s in signups if s["status"] == "Unknown"]
        except Exception as e:
            logger.error(f"Fehler in getUnknownSignups: {e}")
            return []

    return await asyncio.to_thread(_fetch)