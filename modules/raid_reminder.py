import os
import logging
import datetime
import discord
from discord.ext import tasks
from zoneinfo import ZoneInfo
from utils import getCharactersWithDiscordIds, getNextRaid, getUnknownSignups
from config import (
    GUILD_ID, RAID_SIGNUP_CHANNEL_ID
)

logger = logging.getLogger("lunation-bot")

GERMAN_TZ = ZoneInfo("Europe/Berlin")


class RaidReminderClient:
    def __init__(self, client):
        self.client = client
        self.loop = None

    @tasks.loop(time=datetime.time(hour=19, minute=0, tzinfo=GERMAN_TZ))
    async def raid_reminder_loop(self):
        await self.run_reminder()

    async def run_reminder(self):
        client = self.client
        guild = client.get_guild(GUILD_ID)
        if not guild:
            logger.error("Raid-Reminder: Gilde konnte nicht geladen werden.")
            return

        raid_info = await getNextRaid()
        if not raid_info:
            logger.info("Kein Raid gefunden.")
            return

        try:
            raid_date_str = raid_info.get('date')
            raid_date = datetime.datetime.strptime(raid_date_str, "%Y-%m-%d").date()
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            if raid_date != tomorrow:
                logger.info(f"Reminder übersprungen: Raid ist am {raid_date}, heute ist erst der {datetime.date.today()}.")
                return
        except Exception as e:
            logger.error(f"Fehler beim Datumsvergleich: {e}")
            return

        unknown_names = await getUnknownSignups(raid_info["id"])
        if not unknown_names:
            logger.info("Keine Unknown-Signups gefunden.")
            return

        characters = await getCharactersWithDiscordIds()
        if not characters:
            logger.info("Keine Charaktere mit Discord-ID gefunden.")
            return

        char_to_discord = {
            c["name"].lower(): c["note"].strip()
            for c in characters
            if c.get("note") and c["note"].strip().isdigit()
        }

        raid_signup_channel = guild.get_channel(RAID_SIGNUP_CHANNEL_ID)
        raid_string = f"{raid_info.get('instance', {})} {raid_info.get('difficulty', '')} am {raid_date.strftime('%d.%m.%Y')} ({raid_date.strftime('%A')})".strip()

        debug_char = os.getenv("RAID_REMINDER_DEBUG_CHAR")
        if debug_char:
            unknown_names = [debug_char] if debug_char.lower() in [n.lower() for n in unknown_names] else []

        for wow_name in unknown_names:
            discord_id_str = char_to_discord.get(wow_name.lower())
            if not discord_id_str:
                logger.info(f"Keine Discord-ID gefunden für: {wow_name}")
                continue

            discord_id = int(discord_id_str)

            try:
                member = await guild.fetch_member(discord_id)
                if not member:
                    logger.warning(f"Member nicht gefunden: Discord ID {discord_id} (WoW: {wow_name})")
                    continue

                if member.bot:
                    continue

                embed = discord.Embed(
                    title="Erinnerung: Raid-Anmeldung",
                    description=f"Hey {member.mention},\n\ndu bist für den Raid **{raid_string}** aktuell noch als **'Unknown'** gelistet.",
                    color=discord.Color.from_rgb(130, 107, 7)
                )
                embed.add_field(
                    name="",
                    value=f"Bitte gib uns im {raid_signup_channel.mention} Bescheid, ob du dabei bist."
                )
                embed.set_footer(text="Dieser Reminder erfolgt automatisch. Bei Fragen wende dich gerne an die Offiziere.")

                await member.send(embed=embed)
                logger.info(f"DM gesendet an: {member.display_name} (WoW: {wow_name})")
            except discord.NotFound:
                logger.warning(f"Member nicht gefunden: Discord ID {discord_id}")
            except discord.Forbidden:
                logger.warning(f"Konnte {member.display_name} keine DM senden (DMs blockiert).")
            except Exception as e:
                logger.error(f"Fehler beim Senden an {wow_name}: {e}")

    def start(self):
        self.raid_reminder_loop.start()
        logger.info("Raid reminder loop started")


def start_reminder_loop(client):
    reminder = RaidReminderClient(client)
    reminder.start()