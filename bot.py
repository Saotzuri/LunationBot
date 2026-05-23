import os
import logging
from zoneinfo import ZoneInfo
import discord
from discord import app_commands
from dotenv import load_dotenv
from config import GUILD_ID
from modules import bewerbung, kummerkasten, welcome, raid_reminder

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


@client.tree.command(name="bewerbung-setup", description="Postet den Bewerbungs-Embed")
@app_commands.guilds(GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def bewerbung_setup(interaction: discord.Interaction):
    await bewerbung.on_bewerbung_setup(interaction)


@client.tree.command(name="kummerkasten-setup", description="Postet den Kummerkasten-Embed")
@app_commands.guilds(GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def kummerkasten_setup(interaction: discord.Interaction):
    await kummerkasten.on_kummerkasten_setup(interaction)


@client.event
async def on_member_join(member: discord.Member):
    await welcome.on_member_join(member)


@client.event
async def on_ready():
    client.add_view(bewerbung.BewerbungButton())
    client.add_view(kummerkasten.KummerkastenButton())
    client.add_view(kummerkasten.TicketSchliessenView())

    raid_reminder.start_reminder_loop(client)

    logger.info(f"Lunation is ready! Logged in as {client.user}")


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in .env")
        return
    client.run(token)


if __name__ == "__main__":
    main()