import os
import logging
import discord
from discord import app_commands
from dotenv import load_dotenv

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
        guild = discord.Object(id=1498401477104762910)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

client = Lunation()

MEMBER_ROLE_ID = 1498403566208028934
WILLKOMMEN_CHANNEL_ID = 1498404776650735676
RULES_CHANNEL_ID = 1498405058650312754
BEWERBUNG_CHANNEL_ID = 1498614623065215007
OFFIZIER_ROLE_ID = 1498401628347437197
OFFIZIER_PING_CHANNEL_ID = 1499744209798955049
BEWERBUNG_KATEGORIE_ID = 1498612750073462784
TRIAL_ROLE_ID = 1498403894857044040
TRANSCRIPTS_CHANNEL_ID = 1499747813070737518

# Kummerkasten
KUMMERKASTEN_CHANNEL_ID = 1499829416883392744
KUMMERKASTEN_KATEGORIE_ID = 1498405467477643355

# --- Modal ---

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
        kategorie = client.get_channel(BEWERBUNG_KATEGORIE_ID)

        # Berechtigungen: nur Bewerber + Offiziere + Bot sehen den Channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            offizier_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # Privaten Channel erstellen
        privater_channel = await guild.create_text_channel(
            name=f"bewerbung-{interaction.user.name}",
            category=kategorie,
            overwrites=overwrites
        )

        # Bewerbungs-Embed im privaten Channel posten
        embed = discord.Embed(
            title=f"Bewerbung – {interaction.user.name}",
            color=discord.Color.from_rgb(130, 107, 7)
        )
        embed.set_author(
            name=f"{interaction.user.name}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.add_field(name="Klasse & Spec", value=self.klasse.value, inline=False)
        embed.add_field(name="Warcraftlogs", value=self.logs.value, inline=False)
        embed.add_field(name="Erfahrung", value=self.erfahrung.value, inline=False)
        embed.add_field(name="Raidtage", value=self.raidtage.value, inline=False)
        embed.add_field(name="Warum Lunation?", value=self.warum.value, inline=False)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        await privater_channel.send(embed=embed, view=BewerbungEntscheidungView(interaction.user.id, interaction.user.name))

        # Bewerber + Offiziere im privaten Channel begrüßen
        await privater_channel.send(
            f"{interaction.user.mention} Deine Bewerbung ist eingegangen! 🌙\n\n"
            f"Die Gildenleitung meldet sich so schnell wie möglich hier bei dir.\n"
            f"Falls du noch etwas ergänzen möchtest, schreib es einfach hier rein.\n\n"
        )

        # Offiziere im Offizier-Channel pingen
        offizier_ping_channel = client.get_channel(OFFIZIER_PING_CHANNEL_ID)
        if offizier_ping_channel:
            await offizier_ping_channel.send(
                f"{offizier_role.mention} Neue Bewerbung von {interaction.user.mention} eingegangen!\n"
                f"Zum Channel: {privater_channel.mention}"
            )

        logger.info(f"Bewerbung von {interaction.user.name} ({interaction.user.id}) eingegangen, privater Channel erstellt")

        await interaction.response.send_message(
            f"Deine Bewerbung wurde erfolgreich abgeschickt! Schau hier rein: {privater_channel.mention}",
            ephemeral=True
        )


# --- Kummerkasten Ticket System ---

class KummerkastenModal(discord.ui.Modal, title="Kummerkasten Ticket"):
    betreff = discord.ui.TextInput(
        label="Kurze Beschreibung",
        placeholder="Worum geht es?",
        required=True,
        max_length=100
    )
    nachricht = discord.ui.TextInput(
        label="Was liegt dir auf dem Herzen?",
        placeholder="Erzähl uns was dich beschäftigt...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        offizier_role = guild.get_role(OFFIZIER_ROLE_ID)
        kategorie = client.get_channel(KUMMERKASTEN_KATEGORIE_ID)

        # Berechtigungen: nur User + Offiziere + Bot sehen den Channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            offizier_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # Ticket Channel erstellen
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=kategorie,
            overwrites=overwrites
        )

        # Embed im Ticket Channel
        embed = discord.Embed(
            title=f"Kummerkasten Ticket – {self.betreff.value}",
            color=discord.Color.from_rgb(100, 100, 200)
        )
        embed.set_author(
            name=f"{interaction.user.name}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.add_field(name="Beschreibung", value=self.betreff.value, inline=False)
        embed.add_field(name="Nachricht", value=self.nachricht.value, inline=False)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        await ticket_channel.send(
            f"{interaction.user.mention} {offizier_role.mention}",
            embed=embed
        )

        logger.info(f"Kummerkasten Ticket von {interaction.user.name} erstellt, Channel: {ticket_channel.name}")

        await interaction.response.send_message(
            f"Dein Ticket wurde erstellt! Hier kannst du mit uns sprechen: {ticket_channel.mention}",
            ephemeral=True
        )


# --- Button ---

class BewerbungButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Jetzt bewerben",
        style=discord.ButtonStyle.grey,
        emoji="📩",
        custom_id="bewerbung_button"
    )
    async def bewerbung(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BewerbungModal())


class KummerkastenButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ticket erstellen",
        style=discord.ButtonStyle.grey,
        emoji="💬",
        custom_id="kummerkasten_button"
    )
    async def kummerkasten(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KummerkastenModal())


# --- Bewerbung Entscheidung Buttons ---

class BewerbungEntscheidungView(discord.ui.View):
    def __init__(self, bewerber_id: int, bewerber_name: str):
        super().__init__(timeout=None)
        self.bewerber_id = bewerber_id
        self.bewerber_name = bewerber_name

    @discord.ui.button(label="Annehmen", style=discord.ButtonStyle.green, emoji="✅", custom_id="bewerbung_annehmen")
    async def annehmen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.get_role(OFFIZIER_ROLE_ID) in interaction.user.roles:
            await interaction.response.send_message("Nur Offiziere können diese Aktion durchführen.", ephemeral=True)
            return

        # Prüfen ob Channel noch existiert
        if not interaction.channel:
            return

        guild = interaction.guild
        bewerber = guild.get_member(self.bewerber_id)
        trial_role = guild.get_role(TRIAL_ROLE_ID)

        # Transcript erstellen und in den Transcripts-Channel posten
        transcripts_channel = client.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if transcripts_channel:
            embed = discord.Embed(
                title=f"Bewerbung genehmigt – {self.bewerber_name}",
                color=discord.Color.from_rgb(0, 255, 0)
            )
            embed.add_field(name="Bewerber", value=f"<@{self.bewerber_id}>", inline=False)
            embed.add_field(name="Entscheidung", value="Angenommen", inline=False)
            embed.add_field(name="Bearbeitet von", value=interaction.user.mention, inline=False)
            await transcripts_channel.send(embed=embed)

        # Trial-Rolle geben
        if bewerber and trial_role:
            await bewerber.add_roles(trial_role)
            logger.info(f"Trial-Rolle an {bewerber.name} vergeben")

        # DM an Bewerber
        if bewerber:
            try:
                embed = discord.Embed(
                    title="Deine Bewerbung wurde angenommen! 🎉",
                    color=discord.Color.from_rgb(0, 255, 0)
                )
                embed.add_field(name="Willkommen bei Lunation!", value="Deine Bewerbung wurde angenommen. Du hast jetzt die Trial-Rolle erhalten. Wir freuen uns auf dich im Raid!\n\nBei Fragen melde dich gerne bei den Offizieren.", inline=False)
                await bewerber.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Konnte DM an {bewerber.name} nicht senden (DM deaktiviert)")

        # Channel löschen (falls noch vorhanden)
        try:
            await interaction.channel.delete()
            logger.info(f"Bewerbung von {self.bewerber_name} angenommen, Channel gelöscht")
        except discord.NotFound:
            logger.warning(f"Channel bereits gelöscht für {self.bewerber_name}")

    @discord.ui.button(label="Ablehnen", style=discord.ButtonStyle.red, emoji="❌", custom_id="bewerbung_ablehnen")
    async def ablehnen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.get_role(OFFIZIER_ROLE_ID) in interaction.user.roles:
            await interaction.response.send_message("Nur Offiziere können diese Aktion durchführen.", ephemeral=True)
            return

        # Prüfen ob Channel noch existiert
        if not interaction.channel:
            return

        # Transcript erstellen und in den Transcripts-Channel posten
        transcripts_channel = client.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if transcripts_channel:
            embed = discord.Embed(
                title=f"Bewerbung abgelehnt – {self.bewerber_name}",
                color=discord.Color.from_rgb(255, 0, 0)
            )
            embed.add_field(name="Bewerber", value=f"<@{self.bewerber_id}>", inline=False)
            embed.add_field(name="Entscheidung", value="Abgelehnt", inline=False)
            embed.add_field(name="Bearbeitet von", value=interaction.user.mention, inline=False)
            await transcripts_channel.send(embed=embed)

        # DM an Bewerber
        bewerber = interaction.guild.get_member(self.bewerber_id)
        if bewerber:
            try:
                embed = discord.Embed(
                    title="Deine Bewerbung wurde abgelehnt",
                    color=discord.Color.from_rgb(255, 0, 0)
                )
                embed.add_field(name="Schade...", value="Leider wurde deine Bewerbung bei Lunation abgelehnt.\n\nWir wünschen dir viel Erfolg bei deiner Gildensuche!", inline=False)
                await bewerber.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Konnte DM an {bewerber.name} nicht senden (DM deaktiviert)")

        # Bewerbung schließen (falls Channel noch existiert)
        try:
            await interaction.response.send_message("Bewerbung abgelehnt.", ephemeral=True)
            await interaction.channel.delete()
            logger.info(f"Bewerbung von {self.bewerber_name} abgelehnt, Channel gelöscht")
        except discord.NotFound:
            logger.warning(f"Channel bereits gelöscht für {self.bewerber_name}")


# --- Command zum Posten des Bewerbungs-Embeds ---

@client.tree.command(name="bewerbung-setup", description="Postet den Bewerbungs-Embed im aktuellen Channel")
@app_commands.guilds(1498401477104762910)
@app_commands.checks.has_permissions(administrator=True)
async def bewerbung_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Tritt Lunation bei",
        description="Du willst mit uns Cutting Edge erreichen?\nKlick den Button unten und bewirb dich als Trial-Raider.\nDie Gildenleitung meldet sich so schnell wie möglich bei dir.",
        color=discord.Color.from_rgb(130, 107, 7)
    )
    await interaction.channel.send(embed=embed, view=BewerbungButton())
    await interaction.response.send_message("Bewerbungs-Embed wurde gepostet!", ephemeral=True)


@client.tree.command(name="kummerkasten-setup", description="Postet den Kummerkasten-Embed im aktuellen Channel")
@app_commands.guilds(1498401477104762910)
@app_commands.checks.has_permissions(administrator=True)
async def kummerkasten_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Kummerkasten",
        description="Dir liegt etwas auf dem Herzen?\nDu möchtest etwas loswerden oder einfach mit uns sprechen?\nKlick den Button unten und erstelle ein Ticket.\nDie Offiziere melden sich so schnell wie möglich bei dir.",
        color=discord.Color.from_rgb(100, 100, 200)
    )
    await interaction.channel.send(embed=embed, view=KummerkastenButton())
    await interaction.response.send_message("Kummerkasten-Embed wurde gepostet!", ephemeral=True)


# --- Welcome ---

@client.event
async def on_member_join(member: discord.Member):
    logger.info(f"Member joined: {member.name} ({member.id})")

    role = member.guild.get_role(MEMBER_ROLE_ID)
    if role:
        await member.add_roles(role)
        logger.info(f"Assigned role '{role.name}' to {member.name} ({member.id})")

    channel = client.get_channel(WILLKOMMEN_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            color=discord.Color.from_rgb(0, 225, 255)
        )
        embed.add_field(
            name="Willkommen bei Lunation!",
            value=f"{member.mention} Schön das du da bist!\nLies dir die <#{RULES_CHANNEL_ID}> durch und auf in den raid!",
            inline=False
        )
        embed.add_field(
            name="Bewerben",
            value=f"Falls du dich noch Bewerben musst schau hier <#{BEWERBUNG_CHANNEL_ID}> vorbei.",
            inline=False
        )
        await channel.send(embed=embed)
        logger.info(f"Sent welcome message to {member.name} ({member.id}) in channel {WILLKOMMEN_CHANNEL_ID}")


@client.event
async def on_ready():
    client.add_view(BewerbungButton())
    client.add_view(KummerkastenButton())
    logger.info(f"Lunation is ready! Logged in as {client.user}")


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in .env file")
        return
    client.run(token)


if __name__ == "__main__":
    main()