import os
import logging
import discord
from discord import app_commands
from dotenv import load_dotenv
from config import (
    GUILD_ID, WILLKOMMEN_CHANNEL_ID, RULES_CHANNEL_ID,
    MEMBER_ROLE_ID, OFFIZIER_ROLE_ID, BEWERBUNG_KATEGORIE_ID,
    OFFIZIER_PING_CHANNEL_ID, TRIAL_ROLE_ID, TRANSCRIPTS_CHANNEL_ID,
    KUMMERKASTEN_KATEGORIE_ID
)
from utils.wowaudit import wowaudit_api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("lunation-bot")

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class Lunation(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))


client = Lunation()

# --- State ---
auto_post_days = 0
posted_raids = set()


# ======================
# ==== BEWERBUNG ====
# ======================

class BewerbungModal(discord.ui.Modal, title="Bewerbung bei Lunation"):
    klasse = discord.ui.TextInput(
        label="Klasse & Spec",
        placeholder="z.B. Frost Mage, Arms Warrior...",
        required=True,
        max_length=100
    )
    logs = discord.ui.TextInput(
        label="Warcraftlogs",
        placeholder="https://www.warcraftlogs.com/...",
        required=True,
        max_length=200
    )
    erfahrung = discord.ui.TextInput(
        label="Raiderfahrung",
        placeholder="Welche Tiers, wie weit bist du gekommen?",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    raidtage = discord.ui.TextInput(
        label="Raidtage (Mo/Mi/Fr 19-22 Uhr)",
        placeholder="Kannst du regelmäßig an allen drei Tagen dabei sein?",
        required=True,
        max_length=200
    )
    warum = discord.ui.TextInput(
        label="Warum Lunation?",
        placeholder="Warum möchtest du bei uns raiden?",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        offizier_role = guild.get_role(OFFIZIER_ROLE_ID)
        kategorie = guild.get_channel(BEWERBUNG_KATEGORIE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            offizier_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        privater_channel = await guild.create_text_channel(
            name=f"bewerbung-{interaction.user.name}",
            category=kategorie,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"Bewerbung – {interaction.user.name}",
            color=discord.Color.from_rgb(130, 107, 7)
        )
        embed.set_author(name=f"{interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Klasse & Spec", value=self.klasse.value, inline=False)
        embed.add_field(name="Warcraftlogs", value=self.logs.value, inline=False)
        embed.add_field(name="Erfahrung", value=self.erfahrung.value, inline=False)
        embed.add_field(name="Raidtage", value=self.raidtage.value, inline=False)
        embed.add_field(name="Warum Lunation?", value=self.warum.value, inline=False)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        await privater_channel.send(embed=embed, view=BewerbungEntscheidungView(interaction.user.id, interaction.user.name))
        await privater_channel.send(f"{interaction.user.mention} Deine Bewerbung ist eingegangen! 🌙\n\nDie Gildenleitung meldet sich so schnell wie möglich hier bei dir.\n\n")

        offizier_ping_channel = guild.get_channel(OFFIZIER_PING_CHANNEL_ID)
        if offizier_ping_channel:
            await offizier_ping_channel.send(f"{offizier_role.mention} Neue Bewerbung von {interaction.user.mention}!\nZum Channel: {privater_channel.mention}")

        logger.info(f"Bewerbung von {interaction.user.name}")
        await interaction.response.send_message(f"Deine Bewerbung wurde abgeschickt! Schau hier rein: {privater_channel.mention}", ephemeral=True)


class BewerbungButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Jetzt bewerben", style=discord.ButtonStyle.grey, emoji="📩", custom_id="bewerbung_button")
    async def bewerbung(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BewerbungModal())


class BewerbungEntscheidungView(discord.ui.View):
    def __init__(self, bewerber_id: int, bewerber_name: str):
        super().__init__(timeout=None)
        self.bewerber_id = bewerber_id
        self.bewerber_name = bewerber_name

    @discord.ui.button(label="Annehmen", style=discord.ButtonStyle.green, emoji="✅", custom_id="bewerbung_annehmen")
    async def annehmen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.get_role(OFFIZIER_ROLE_ID) in interaction.user.roles:
            await interaction.response.send_message("Nur Offiziere!", ephemeral=True)
            return

        guild = interaction.guild
        bewerber = guild.get_member(self.bewerber_id)
        trial_role = guild.get_role(TRIAL_ROLE_ID)
        transcripts_channel = guild.get_channel(TRANSCRIPTS_CHANNEL_ID)

        if transcripts_channel:
            embed = discord.Embed(title=f"Bewerbung genehmigt – {self.bewerber_name}", color=discord.Color.from_rgb(0, 255, 0))
            embed.add_field(name="Bewerber", value=f"<@{self.bewerber_id}>")
            embed.add_field(name="Entscheidung", value="Angenommen")
            await transcripts_channel.send(embed=embed)

        if bewerber and trial_role:
            await bewerber.add_roles(trial_role)

        if bewerber:
            try:
                await bewerber.send(embed=discord.Embed(title="Deine Bewerbung wurde angenommen! 🎉", color=discord.Color.from_rgb(0, 255, 0), description="Willkommen bei Lunation! Du hast die Trial-Rolle erhalten."))
            except:
                pass

        try:
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="Ablehnen", style=discord.ButtonStyle.red, emoji="❌", custom_id="bewerbung_ablehnen")
    async def ablehnen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.get_role(OFFIZIER_ROLE_ID) in interaction.user.roles:
            await interaction.response.send_message("Nur Offiziere!", ephemeral=True)
            return

        transcripts_channel = interaction.guild.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if transcripts_channel:
            embed = discord.Embed(title=f"Bewerbung abgelehnt – {self.bewerber_name}", color=discord.Color.from_rgb(255, 0, 0))
            embed.add_field(name="Bewerber", value=f"<@{self.bewerber_id}>")
            embed.add_field(name="Entscheidung", value="Abgelehnt")
            await transcripts_channel.send(embed=embed)

        bewerber = interaction.guild.get_member(self.bewerber_id)
        if bewerber:
            try:
                await bewerber.send(embed=discord.Embed(title="Deine Bewerbung wurde abgelehnt", color=discord.Color.from_rgb(255, 0, 0), description="Schade... Wir wünschen dir viel Erfolg bei deiner Gildensuche!"))
            except:
                pass

        try:
            await interaction.response.send_message("Abgelehnt.", ephemeral=True)
            await interaction.channel.delete()
        except:
            pass


@client.tree.command(name="bewerbung-setup", description="Postet den Bewerbungs-Embed")
@app_commands.guilds(GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def bewerbung_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Tritt Lunation bei",
        description="Du willst mit uns Cutting Edge erreichen?\nKlick den Button unten und bewirb dich!",
        color=discord.Color.from_rgb(130, 107, 7)
    )
    await interaction.channel.send(embed=embed, view=BewerbungButton())
    await interaction.response.send_message("Bewerbungs-Embed gepostet!", ephemeral=True)


# ======================
# ==== KUMMERKASTEN ====
# ======================

class KummerkastenModal(discord.ui.Modal, title="Kummerkasten Ticket"):
    betreff = discord.ui.TextInput(label="Kurze Beschreibung", placeholder="Worum geht es?", required=True, max_length=100)
    nachricht = discord.ui.TextInput(label="Was liegt dir auf dem Herzen?", placeholder="Erzähl uns...", required=True, style=discord.TextStyle.paragraph, max_length=1500)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        offizier_role = guild.get_role(OFFIZIER_ROLE_ID)
        kategorie = guild.get_channel(KUMMERKASTEN_KATEGORIE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            offizier_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=kategorie, overwrites=overwrites)

        embed = discord.Embed(title=f"Kummerkasten Ticket – {self.betreff.value}", color=discord.Color.from_rgb(100, 100, 200))
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Beschreibung", value=self.betreff.value)
        embed.add_field(name="Nachricht", value=self.nachricht.value)

        await ticket_channel.send(f"{interaction.user.mention} {offizier_role.mention}", embed=embed, view=TicketSchliessenView())
        await interaction.response.send_message(f"Ticket erstellt: {ticket_channel.mention}", ephemeral=True)


class KummerkastenButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket erstellen", style=discord.ButtonStyle.grey, emoji="💬", custom_id="kummerkasten_button")
    async def kummerkasten(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KummerkastenModal())


class TicketSchliessenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket schließen", style=discord.ButtonStyle.red, emoji="🔒", custom_id="ticket_schliessen")
    async def schliessen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.get_role(OFFIZIER_ROLE_ID) in interaction.user.roles:
            await interaction.response.send_message("Nur Offiziere!", ephemeral=True)
            return
        await interaction.response.send_message("Ticket wird geschlossen...", ephemeral=True)
        await interaction.channel.delete()


@client.tree.command(name="kummerkasten-setup", description="Postet den Kummerkasten-Embed")
@app_commands.guilds(GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def kummerkasten_setup(interaction: discord.Interaction):
    embed = discord.Embed(title="Kummerkasten", description="Dir liegt etwas auf dem Herzen?\nKlick den Button unten!", color=discord.Color.from_rgb(100, 100, 200))
    await interaction.channel.send(embed=embed, view=KummerkastenButton())
    await interaction.response.send_message("Kummerkasten-Embed gepostet!", ephemeral=True)


# ======================
# ==== RAID EVENTS ====
# ======================

import asyncio
from datetime import datetime, timedelta


@client.tree.command(name="subscribe", description="Aktiviert automatisches Raid Event Posting")
@app_commands.guilds(GUILD_ID)
@app_commands.describe(tage="Anzahl Tage (1-14)")
@app_commands.checks.has_permissions(administrator=True)
async def subscribe(interaction: discord.Interaction, tage: int):
    global auto_post_days
    if tage < 1 or tage > 14:
        await interaction.response.send_message("Bitte 1-14 eingeben.", ephemeral=True)
        return

    auto_post_days = tage
    logger.info(f"Auto-posting aktiviert für {tage} Tage")
    await interaction.response.send_message(f"✅ Automatisches Raid Event Posting aktiviert für **{tage} Tage**!", ephemeral=True)
    await post_raids()


@client.tree.command(name="unsubscribe", description="Deaktiviert automatisches Raid Event Posting")
@app_commands.guilds(GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def unsubscribe(interaction: discord.Interaction):
    global auto_post_days, posted_raids
    auto_post_days = 0
    posted_raids.clear()
    await interaction.response.send_message("✅ Auto-posting **deaktiviert**!", ephemeral=True)


@client.tree.command(name="sync-events", description="Synchronisiert Raids mit Discord Events")
@app_commands.guilds(GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def sync_events(interaction: discord.Interaction):
    if not wowaudit_api or not wowaudit_api.is_configured:
        await interaction.response.send_message("WoWAudit API nicht konfiguriert!", ephemeral=True)
        return

    await interaction.response.send_message("Synchronisiere Raids...", ephemeral=True)
    count = await post_raids()
    await interaction.edit_original_response(content=f"✅ {count} Raid Events erstellt!")


async def post_raids() -> int:
    """Postet alle kommenden Raids als Discord Events"""
    if not wowaudit_api or not wowaudit_api.is_configured:
        return 0

    try:
        raids = wowaudit_api.get_raids()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Raids: {e}")
        return 0

    # Debug: Print response structure
    logger.info(f"API Response: {raids}")

    # Handle different response formats
    if isinstance(raids, dict):
        # Check common keys
        if "raids" in raids:
            raids = raids["raids"]
        elif "data" in raids:
            raids = raids["data"]
        else:
            logger.warning(f"Unknown dict keys: {raids.keys()}")
            return 0
    elif isinstance(raids, str):
        logger.warning(f"API returned string: {raids}")
        return 0
    elif not isinstance(raids, list):
        logger.warning(f"Unknown response type: {type(raids)}")
        return 0

    guild = client.get_guild(GUILD_ID)
    if not guild:
        return 0

    # Use timezone-aware datetime
    tz = datetime.now().astimezone().tzinfo
    now = datetime.now(tz)
    cutoff = now + timedelta(days=auto_post_days)
    count = 0

    for raid in raids:
        if isinstance(raid, str):
            continue
        raid_id = raid.get("id")
        if not raid_id or raid_id in posted_raids:
            continue

        raid_date_str = raid.get("date", "")
        raid_time = raid.get("start_time", "19:00")
        raid_end_time = raid.get("end_time", "22:00")
        raid_name = f"{raid.get('instance', 'Raid')} ({raid.get('difficulty', 'Mythic')})"
        optional = raid.get("optional", False)
        status = raid.get("status", "Planned")

        # Skip past raids
        if status == "Locked":
            continue

        try:
            raid_date = datetime.strptime(raid_date_str, "%Y-%m-%d")
            hour, minute = map(int, raid_time.split(":"))
            raid_datetime = raid_date.replace(hour=hour, minute=minute).astimezone(tz)
            end_hour, end_minute = map(int, raid_end_time.split(":"))
            raid_end_datetime = raid_date.replace(hour=end_hour, minute=end_minute).astimezone(tz)
        except Exception as e:
            logger.warning(f"Date parse error: {e}")
            continue

        if now <= raid_datetime <= cutoff:
            try:
                description = f"{status}"
                if optional:
                    description += " (optional)"
                description += f"\n\n{' - '.join(raid.get('instances', []))}"

                await guild.create_scheduled_event(
                    name=f"📅 {raid_name}",
                    description=description,
                    start_time=raid_datetime,
                    end_time=raid_end_datetime,
                    location="WoWAudit",
                    entity_type=discord.ScheduledEventEntityType.external,
                    privacy_level=discord.PrivacyLevel.guild_only
                )
                posted_raids.add(raid_id)
                count += 1
                logger.info(f"Event erstellt: {raid_name}")
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Events: {e}")

    return count


# ======================
# ==== WELCOME ====
# ======================

@client.event
async def on_member_join(member: discord.Member):
    logger.info(f"Member joined: {member.name}")

    role = member.guild.get_role(MEMBER_ROLE_ID)
    if role:
        await member.add_roles(role)

    channel = member.guild.get_channel(WILLKOMMEN_CHANNEL_ID)
    if channel:
        embed = discord.Embed(color=discord.Color.from_rgb(0, 225, 255))
        embed.add_field(name="Willkommen bei Lunation!", value=f"{member.mention} Schön das du da bist!\nLies dir die <#{RULES_CHANNEL_ID}> durch!", inline=False)
        await channel.send(embed=embed)


@client.event
async def on_ready():
    client.add_view(BewerbungButton())
    client.add_view(KummerkastenButton())
    client.add_view(TicketSchliessenView())
    logger.info(f"Lunation is ready! Logged in as {client.user}")


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in .env")
        return
    client.run(token)


if __name__ == "__main__":
    main()