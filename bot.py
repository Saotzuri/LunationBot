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
        channel = client.get_channel(BEWERBUNG_CHANNEL_ID)

        # Bewerbungs-Embed
        embed = discord.Embed(
            title=f"Neue Bewerbung – {interaction.user.name}",
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

        if channel:
            # Bewerbung posten + Offiziere pingen
            offizier_role = interaction.guild.get_role(OFFIZIER_ROLE_ID)
            bewerbung_msg = await channel.send(
                content=f"{offizier_role.mention} Neue Bewerbung eingegangen!",
                embed=embed
            )

            # Thread erstellen
            thread = await bewerbung_msg.create_thread(
                name=f"Bewerbung – {interaction.user.name}",
                auto_archive_duration=10080  # 7 Tage
            )

            # Bewerber + Offiziere in Thread einladen
            await thread.send(
                f"{interaction.user.mention} Deine Bewerbung ist eingegangen! 🌙\n\n"
                f"Die Gildenleitung meldet sich so schnell wie möglich hier bei dir.\n"
                f"Falls du noch etwas ergänzen möchtest, schreib es einfach hier rein.\n\n"
                f"{offizier_role.mention}"
            )

            logger.info(f"Bewerbung von {interaction.user.name} ({interaction.user.id}) eingegangen, Thread erstellt")

        await interaction.response.send_message(
            "Deine Bewerbung wurde erfolgreich abgeschickt! Schau in den Bewerbungs-Channel, dort wurde ein Thread für dich geöffnet.",
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


# --- Command zum Posten des Bewerbungs-Embeds ---

@client.tree.command(name="bewerbung-setup", description="Postet den Bewerbungs-Embed im aktuellen Channel")
@app_commands.guilds(1498401477104762910)
@app_commands.checks.has_permissions(administrator=True)
async def bewerbung_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Tritt Lunation bei",
        description="Du willst mit uns Cutting Edge erreichen?\nKlick den Button unten und bewirb dich als Trial-Raider.\nDie Gildenleitung meldet sich so schnell wie möglich bei dir.",
        color=discord.Color.from_rgb(0, 225, 255)
    )
    await interaction.channel.send(embed=embed, view=BewerbungButton())
    await interaction.response.send_message("Bewerbungs-Embed wurde gepostet!", ephemeral=True)


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
    logger.info(f"Lunation is ready! Logged in as {client.user}")


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in .env file")
        return
    client.run(token)


if __name__ == "__main__":
    main()