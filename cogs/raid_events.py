import discord
import logging
import asyncio
from discord import app_commands
from datetime import datetime, timedelta
from config import GUILD_ID, OFFIZIER_ROLE_ID
from utils.wowaudit import wowaudit_api

logger = logging.getLogger("lunation-bot")

# Auto-posting state
auto_post_days = 0
posted_raids = set()


class RaidEventsCog(discord.app_commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bg_task = None

    @discord.app_commands.command(name="subscribe", description="Aktiviert automatisches Raid Event Posting")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(tage="Anzahl Tage für automatische Events (1-14)")
    @app_commands.checks.has_permissions(administrator=True)
    async def subscribe(self, interaction: discord.Interaction, tage: int):
        global auto_post_days

        if tage < 1 or tage > 14:
            await interaction.response.send_message("Bitte eine Zahl zwischen 1 und 14 eingeben.", ephemeral=True)
            return

        auto_post_days = tage
        logger.info(f"Auto-posting aktiviert für {tage} Tage")

        await interaction.response.send_message(
            f"✅ Automatisches Raid Event Posting aktiviert für die nächsten **{tage} Tage**!\n"
            f"Raids werden automatisch als Discord Events erstellt.",
            ephemeral=True
        )

        # Events sofort posten
        await self.post_raids()

    @discord.app_commands.command(name="unsubscribe", description="Deaktiviert automatisches Raid Event Posting")
    @app_commands.guilds(GUILD_ID)
    @app_commands.checks.has_permissions(administrator=True)
    async def unsubscribe(self, interaction: discord.Interaction):
        global auto_post_days, posted_raids

        auto_post_days = 0
        posted_raids.clear()

        logger.info("Auto-posting deaktiviert")

        await interaction.response.send_message(
            "✅ Automatisches Raid Event Posting **deaktiviert**!",
            ephemeral=True
        )

    @discord.app_commands.command(name="sync-events", description="Synchronisiert Raids mit Discord Events")
    @app_commands.guilds(GUILD_ID)
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_events(self, interaction: discord.Interaction):
        if not wowaudit_api or not wowaudit_api.is_configured:
            await interaction.response.send_message("WoWAudit API ist nicht konfiguriert!", ephemeral=True)
            return

        await interaction.response.send_message("Synchronisiere Raids...", ephemeral=True)
        await self.post_raids()
        await interaction.edit_original_response(content=f"✅ {len(posted_raids)} Raids als Events erstellt!")

    async def post_raids(self):
        """Postet alle kommenden Raids als Discord Events"""
        if not wowaudit_api or not wowaudit_api.is_configured:
            logger.warning("WoWAudit API nicht konfiguriert")
            return

        try:
            raids = wowaudit_api.get_raids()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Raids: {e}")
            return

        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        now = datetime.now()
        cutoff = now + timedelta(days=auto_post_days)

        posted_count = 0

        for raid in raids:
            raid_id = raid.get("id")
            if not raid_id or raid_id in posted_raids:
                continue

            raid_date_str = raid.get("date", "")
            raid_time = raid.get("time", "19:00")
            raid_name = raid.get("name", f"Raid {raid_id}")
            raid_note = raid.get("note", "")

            # Datum parsen
            try:
                raid_date = datetime.strptime(raid_date_str, "%A, %B %d, %Y")
                raid_date = raid_date.replace(year=now.year)

                # Zeit hinzufügen
                hour, minute = map(int, raid_time.split(":"))
                raid_datetime = raid_date.replace(hour=hour, minute=minute)
            except:
                continue

            # Nur Raids in den nächsten X Tagen
            if now <= raid_datetime <= cutoff:
                # Discord Scheduled Event erstellen
                try:
                    event = await guild.create_scheduled_event(
                        name=f"📅 {raid_name}",
                        description=raid_note or "Raider gefragt!",
                        start_time=raid_datetime,
                        end_time=raid_datetime + timedelta(hours=3),
                        location="WoWAudit",
                        privacy_level=discord.PrivacyLevel.guild_only
                    )
                    posted_raids.add(raid_id)
                    posted_count += 1
                    logger.info(f"Event erstellt: {raid_name} am {raid_date_str}")
                except Exception as e:
                    logger.error(f"Fehler beim Erstellen des Events: {e}")

        logger.info(f"Automatisch {posted_count} Raid Events gepostet")

    async def cleanup_old_events(self):
        """Löscht Events die älter als 1 Tag sind"""
        if not wowaudit_api or not wowaudit_api.is_configured:
            return

        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        try:
            raids = wowaudit_api.get_raids()
        except:
            return

        now = datetime.now()
        yesterday = now - timedelta(days=1)

        for raid in raids:
            raid_id = raid.get("id")
            if not raid_id or raid_id not in posted_raids:
                continue

            raid_date_str = raid.get("date", "")
            raid_time = raid.get("time", "19:00")

            try:
                raid_date = datetime.strptime(raid_date_str, "%A, %B %d, %Y")
                raid_date = raid_date.replace(year=now.year)
                hour, minute = map(int, raid_time.split(":"))
                raid_datetime = raid_date.replace(hour=hour, minute=minute)
            except:
                continue

            # Wenn Raid gestern war, Event löschen
            if raid_datetime <= yesterday:
                # Discord Event finden und löschen
                events = await guild.fetch_scheduled_events()
                for event in events:
                    if str(raid_id) in event.name or raid_date_str in event.name:
                        try:
                            await event.delete()
                            logger.info(f"Event gelöscht: {event.name}")
                        except:
                            pass

                posted_raids.discard(raid_id)

    async def cog_load(self):
        # Background Task starten
        self.bg_task = asyncio.create_task(self.background_loop())

    async def cog_unload(self):
        if self.bg_task:
            self.bg_task.cancel()

    async def background_loop(self):
        """Läuft alle 30 Minuten und prüft auf neue Raids"""
        while True:
            try:
                await asyncio.sleep(1800)  # 30 Minuten

                if auto_post_days > 0:
                    await self.post_raids()
                    await self.cleanup_old_events()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background loop error: {e}")
                await asyncio.sleep(60)


async def setup(bot):
    await bot.add_cog(RaidEventsCog(bot))