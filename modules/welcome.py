import logging
import discord
from config import (
    WILLKOMMEN_CHANNEL_ID, RULES_CHANNEL_ID,
    BEWERBUNG_CHANNEL_ID, MEMBER_ROLE_ID
)

logger = logging.getLogger("lunation-bot")


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