import os
import discord
from discord import app_commands
from dotenv import load_dotenv

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
    role = member.guild.get_role(MEMBER_ROLE_ID)
    if role:
        await member.add_roles(role)

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


@client.event
async def on_ready():
    print(f"Lunation is ready! Logged in as {client.user}")


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in .env file")
        return

    client.run(token)


if __name__ == "__main__":
    main()