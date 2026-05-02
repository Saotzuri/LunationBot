import discord
import logging
from discord import app_commands
from config import (
    GUILD_ID, OFFIZIER_ROLE_ID, BEWERBUNG_KATEGORIE_ID,
    OFFIZIER_PING_CHANNEL_ID, TRIAL_ROLE_ID, TRANSCRIPTS_CHANNEL_ID
)

logger = logging.getLogger("lunation-bot")


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

        await privater_channel.send(
            f"{interaction.user.mention} Deine Bewerbung ist eingegangen! 🌙\n\n"
            f"Die Gildenleitung meldet sich so schnell wie möglich hier bei dir.\n"
            f"Falls du noch etwas ergänzen möchtest, schreib es einfach hier rein.\n\n"
        )

        offizier_ping_channel = guild.get_channel(OFFIZIER_PING_CHANNEL_ID)
        if offizier_ping_channel:
            await offizier_ping_channel.send(
                f"{offizier_role.mention} Neue Bewerbung von {interaction.user.mention} eingegangen!\n"
                f"Zum Channel: {privater_channel.mention}"
            )

        logger.info(f"Bewerbung von {interaction.user.name} ({interaction.user.id}) eingegangen")

        await interaction.response.send_message(
            f"Deine Bewerbung wurde erfolgreich abgeschickt! Schau hier rein: {privater_channel.mention}",
            ephemeral=True
        )


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

        if not interaction.channel:
            return

        guild = interaction.guild
        bewerber = guild.get_member(self.bewerber_id)
        trial_role = guild.get_role(TRIAL_ROLE_ID)

        transcripts_channel = guild.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if transcripts_channel:
            embed = discord.Embed(
                title=f"Bewerbung genehmigt – {self.bewerber_name}",
                color=discord.Color.from_rgb(0, 255, 0)
            )
            embed.add_field(name="Bewerber", value=f"<@{self.bewerber_id}>", inline=False)
            embed.add_field(name="Entscheidung", value="Angenommen", inline=False)
            embed.add_field(name="Bearbeitet von", value=interaction.user.mention, inline=False)
            await transcripts_channel.send(embed=embed)

        if bewerber and trial_role:
            await bewerber.add_roles(trial_role)
            logger.info(f"Trial-Rolle an {bewerber.name} vergeben")

        if bewerber:
            try:
                embed = discord.Embed(
                    title="Deine Bewerbung wurde angenommen! 🎉",
                    color=discord.Color.from_rgb(0, 255, 0)
                )
                embed.add_field(name="Willkommen bei Lunation!", value="Deine Bewerbung wurde angenommen. Du hast jetzt die Trial-Rolle erhalten. Wir freuen uns auf dich im Raid!\n\nBei Fragen melde dich gerne bei den Offizieren.", inline=False)
                await bewerber.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Konnte DM an {bewerber.name} nicht senden")

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

        if not interaction.channel:
            return

        transcripts_channel = interaction.guild.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if transcripts_channel:
            embed = discord.Embed(
                title=f"Bewerbung abgelehnt – {self.bewerber_name}",
                color=discord.Color.from_rgb(255, 0, 0)
            )
            embed.add_field(name="Bewerber", value=f"<@{self.bewerber_id}>", inline=False)
            embed.add_field(name="Entscheidung", value="Abgelehnt", inline=False)
            embed.add_field(name="Bearbeitet von", value=interaction.user.mention, inline=False)
            await transcripts_channel.send(embed=embed)

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
                logger.warning(f"Konnte DM an {bewerber.name} nicht senden")

        try:
            await interaction.response.send_message("Bewerbung abgelehnt.", ephemeral=True)
            await interaction.channel.delete()
            logger.info(f"Bewerbung von {self.bewerber_name} abgelehnt")
        except discord.NotFound:
            logger.warning(f"Channel bereits gelöscht für {self.bewerber_name}")


class BewerbungCommands:
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bewerbung-setup", description="Postet den Bewerbungs-Embed im aktuellen Channel")
    @app_commands.guilds(GUILD_ID)
    @app_commands.checks.has_permissions(administrator=True)
    async def bewerbung_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Tritt Lunation bei",
            description="Du willst mit uns Cutting Edge erreichen?\nKlick den Button unten und bewirb dich als Trial-Raider.\nDie Gildenleitung meldet sich so schnell wie möglich bei dir.",
            color=discord.Color.from_rgb(130, 107, 7)
        )
        await interaction.channel.send(embed=embed, view=BewerbungButton())
        await interaction.response.send_message("Bewerbungs-Embed wurde gepostet!", ephemeral=True)


def setup(bot):
    bot.add_view(BewerbungButton())
    bot.add_tree_exchange(BewerbungCommands(bot))