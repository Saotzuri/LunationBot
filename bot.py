import os
import logging
import discord
from discord import app_commands
from dotenv import load_dotenv
from config import GUILD_ID, WILLKOMMEN_CHANNEL_ID, RULES_CHANNEL_ID, MEMBER_ROLE_ID

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


# --- Welcome System ---

@client.event
async def on_member_join(member: discord.Member):
    logger.info(f"Member joined: {member.name} ({member.id})")

    role = member.guild.get_role(MEMBER_ROLE_ID)
    if role:
        await member.add_roles(role)
        logger.info(f"Assigned role '{role.name}' to {member.name}")

    channel = member.guild.get_channel(WILLKOMMEN_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            color=discord.Color.from_rgb(0, 225, 255)
        )
        embed.add_field(
            name="Willkommen bei Lunation!",
            value=f"{member.mention} Schön das du da bist!\nLies dir die <#{RULES_CHANNEL_ID}> durch und auf in den raid!",
            inline=False
        )
        await channel.send(embed=embed)
        logger.info(f"Sent welcome message to {member.name}")


@client.event
async def on_ready():
    logger.info(f"Lunation is ready! Logged in as {client.user}")


def main():
    # Cogs laden
    from cogs.bewerbung import setup as bewerbung_setup
    from cogs.kummerkasten import setup as kummerkasten_setup
    from cogs.raid_events import setup as raid_events_setup

    client.loop.create_task(raid_events_setup(client))

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in .env file")
        return

    client.run(token)


if __name__ == "__main__":
    main()