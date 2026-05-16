import os
import logging
from zoneinfo import ZoneInfo
import discord
import datetime
import requests
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv
from config import (
    GUILD_ID, RAID_SIGNUP_CHANNEL_ID, RAIDER_ROLE_ID, WILLKOMMEN_CHANNEL_ID, RULES_CHANNEL_ID,
    MEMBER_ROLE_ID, BEWERBUNG_CHANNEL_ID,
    OFFIZIER_ROLE_ID, BEWERBUNG_KATEGORIE_ID,
    OFFIZIER_PING_CHANNEL_ID, TRIAL_ROLE_ID, TRANSCRIPTS_CHANNEL_ID,
    KUMMERKASTEN_KATEGORIE_ID
)

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

GERMAN_TZ = ZoneInfo("Europe/Berlin")

class Lunation(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        self.raid_reminder_loop.start()

    @tasks.loop(time=datetime.time(hour=19, minute=0, tzinfo=GERMAN_TZ))
    # @tasks.loop(minutes=1)
    async def raid_reminder_loop(self):
        await self.wait_until_ready()
        await raidReminder(self)

client = Lunation()


# ======================
# ==== BEWERBUNG ====
# ======================

class BewerbungModal(discord.ui.Modal, title="Bewerbung bei Lunation"):
    klasse = discord.ui.TextInput(label="Klasse & Spec", placeholder="z.B. Frost Mage, Arms Warrior...", required=True, max_length=100)
    logs = discord.ui.TextInput(label="Warcraftlogs", placeholder="https://www.warcraftlogs.com/...", required=True, max_length=200)
    erfahrung = discord.ui.TextInput(label="Raiderfahrung", placeholder="Welche Tiers, wie weit bist du gekommen?", required=True, style=discord.TextStyle.paragraph, max_length=500)
    raidtage = discord.ui.TextInput(label="Raidtage (Mo/Mi/Fr 19-22 Uhr)", placeholder="Kannst du regelmäßig an allen drei Tagen dabei sein?", required=True, max_length=200)
    warum = discord.ui.TextInput(label="Warum Lunation?", placeholder="Warum möchtest du bei uns raiden?", required=True, style=discord.TextStyle.paragraph, max_length=500)

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

        privater_channel = await guild.create_text_channel(name=f"bewerbung-{interaction.user.name}", category=kategorie, overwrites=overwrites)

        embed = discord.Embed(title=f"Bewerbung – {interaction.user.name}", color=discord.Color.from_rgb(130, 107, 7))
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
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
            embed.add_field(name="Bewerber", value=f"<@{self.bewerber_id}>", inline=False)
            embed.add_field(name="Entscheidung", value="Angenommen", inline=False)
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

        await interaction.response.send_modal(BewerbungAblehnenModal(self.bewerber_id, self.bewerber_name))


class BewerbungAblehnenModal(discord.ui.Modal, title="Bewerbung ablehnen"):
    grund = discord.ui.TextInput(label="Grund der Ablehnung", placeholder="Warum wird die Bewerbung abgelehnt?", style=discord.TextStyle.paragraph, required=True, max_length=1000)

    def __init__(self, bewerber_id: int, bewerber_name: str):
        super().__init__(timeout=None)
        self.bewerber_id = bewerber_id
        self.bewerber_name = bewerber_name

    async def on_submit(self, interaction: discord.Interaction):
        transcripts_channel = interaction.guild.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if transcripts_channel:
            embed = discord.Embed(title=f"Bewerbung abgelehnt – {self.bewerber_name}", color=discord.Color.from_rgb(255, 0, 0))
            embed.add_field(name="Bewerber", value=f"<@{self.bewerber_id}>", inline=False)
            embed.add_field(name="Entscheidung", value="Abgelehnt", inline=False)
            embed.add_field(name="Grund", value=self.grund.value, inline=False)
            await transcripts_channel.send(embed=embed)

        bewerber = interaction.guild.get_member(self.bewerber_id)
        if bewerber:
            try:
                embed = discord.Embed(title="Deine Bewerbung wurde abgelehnt", color=discord.Color.from_rgb(255, 0, 0))
                embed.add_field(name="Schade... Wir wünschen dir viel Erfolg bei deiner Gildensuche!", value=self.grund.value, inline=False)
                await bewerber.send(embed=embed)
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
    embed = discord.Embed(title="Tritt Lunation bei", description="Du willst mit uns Cutting Edge erreichen?\nKlick den Button unten und bewirb dich!", color=discord.Color.from_rgb(130, 107, 7))
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
# ==== WELCOME ====
# ======================

@client.event
async def on_member_join(member: discord.Member):
    logger.info(f"Member joined: {member.name}")

    role = member.guild.get_role(MEMBER_ROLE_ID)
    if role:
        await member.add_roles(role)

    channel = member.guild.get_channel(WILLKOMMEN_CHANNEL_ID)
    rules_channel = member.guild.get_channel(RULES_CHANNEL_ID)
    bewerbung_channel = member.guild.get_channel(BEWERBUNG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(color=discord.Color.from_rgb(0, 225, 255))
        embed.add_field(
            name="Willkommen bei Lunation!",
            value=f"{member.mention} Schön das du da bist!\n"
                  f"Lies dir die {rules_channel.mention} durch und auf in den raid!\n\n",
            inline=False
        )
        embed.add_field(
            name="Bewerben",
            value=f"Falls du dich noch bewerben musst schau hier {bewerbung_channel.mention} vorbei.",
            inline=False
        )
        await channel.send(embed=embed)

# ======================
# ==== RAID REMINDER ====
# ======================

WOWAUDIT_API_KEY = os.getenv("WOWAUDIT_TOKEN")
WOWAUDIT_API_URL = os.getenv("WOWAUDIT_API_URL", "https://www.wowaudit.com")

async def getCharactersWithDiscordIds():
    headers = {'accept': 'application/json', 'Authorization': WOWAUDIT_API_KEY}
    characters_url = f'{WOWAUDIT_API_URL}/v1/characters'

    try:
        response = requests.get(characters_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Fehler beim Laden der Charaktere: {response.status_code}")
            return []

        characters = response.json()
        # note enthält die Discord User ID
        return [c for c in characters if c.get("note")]
    except Exception as e:
        logger.error(f"Fehler in getCharactersWithDiscordIds: {e}")
        return []

async def getNextRaid():
    headers = {'accept': 'application/json', 'Authorization': WOWAUDIT_API_KEY}
    raids_url = f'{WOWAUDIT_API_URL}/v1/raids?include_past=false'

    try:
        response = requests.get(raids_url, headers=headers)
        if response.status_code != 200: return None

        raids = response.json().get("raids", [])
        if not raids: return None
        return raids[0]
    except Exception as e:
        logger.error(f"Fehler in getNextRaid: {e}")
        return None

async def getUnknownSignups(raid_id):
    headers = {'accept': 'application/json', 'Authorization': WOWAUDIT_API_KEY}
    details_url = f'{WOWAUDIT_API_URL}/v1/raids/{raid_id}'

    try:
        response = requests.get(details_url, headers=headers)
        if response.status_code != 200: return []

        signups = response.json().get("signups", [])
        return [s["character"]["name"] for s in signups if s["status"] == "Unknown"]
    except Exception as e:
        logger.error(f"Fehler in getUnknownSignups: {e}")
        return []

async def raidReminder(self):
    guild = self.get_guild(GUILD_ID)
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

    # Unknown-Signups vom nächsten Raid holen
    unknown_names = await getUnknownSignups(raid_info["id"])
    if not unknown_names:
        logger.info("Keine Unknown-Signups gefunden.")
        return

    # Characters mit Discord-IDs holen
    characters = await getCharactersWithDiscordIds()
    if not characters:
        logger.info("Keine Charaktere mit Discord-ID gefunden.")
        return

    # Mapping: char_name -> discord_id
    char_to_discord = {
        c["name"].lower(): c["note"].strip()
        for c in characters
        if c.get("note") and c["note"].strip().isdigit()
    }

    raid_signup_channel = guild.get_channel(RAID_SIGNUP_CHANNEL_ID)
    raid_string = f"{raid_info.get('instance', {})} {raid_info.get('difficulty', '')} am {raid_date.strftime('%d.%m.%Y')} ({raid_date.strftime('%A')})".strip()

    # Debug: Nur an bestimmten Charakter senden (z.B. "Magemitcasio")
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