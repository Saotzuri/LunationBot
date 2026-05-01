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
        await self.tree.sync()

client = Lunation()

MEMBER_ROLE_ID = 1498403566208028934
WILLKOMMEN_CHANNEL_ID = 1498404776650735676
RULES_CHANNEL_ID = 1498405058650312754
BEWERBUNG_CHANNEL_ID = 1498614623065215007


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
    logger.info(f"Lunation is ready! Logged in as {client.user}")


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in .env file")
        return

    client.run(token)


if __name__ == "__main__":
    main()