import discord
import logging
from discord import app_commands
from config import GUILD_ID, OFFIZIER_ROLE_ID, KUMMERKASTEN_KATEGORIE_ID

logger = logging.getLogger("lunation-bot")


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
        kategorie = guild.get_channel(KUMMERKASTEN_KATEGORIE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            offizier_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=kategorie,
            overwrites=overwrites
        )

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
            embed=embed,
            view=TicketSchliessenView()
        )

        logger.info(f"Kummerkasten Ticket von {interaction.user.name} erstellt")

        await interaction.response.send_message(
            f"Dein Ticket wurde erstellt! Hier kannst du mit uns sprechen: {ticket_channel.mention}",
            ephemeral=True
        )


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


class TicketSchliessenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket schließen", style=discord.ButtonStyle.red, emoji="🔒", custom_id="ticket_schliessen")
    async def schliessen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.get_role(OFFIZIER_ROLE_ID) in interaction.user.roles:
            await interaction.response.send_message("Nur Offiziere können Tickets schließen.", ephemeral=True)
            return

        await interaction.response.send_message("Ticket wird geschlossen...", ephemeral=True)
        await interaction.channel.delete()
        logger.info(f"Kummerkasten Ticket geschlossen von {interaction.user.name}")


class KummerkastenCog(discord.app_commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="kummerkasten-setup", description="Postet den Kummerkasten-Embed im aktuellen Channel")
    @app_commands.guilds(GUILD_ID)
    @app_commands.checks.has_permissions(administrator=True)
    async def kummerkasten_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Kummerkasten",
            description="Dir liegt etwas auf dem Herzen?\nDu möchtest etwas loswerden oder einfach mit uns sprechen?\nKlick den Button unten und erstelle ein Ticket.\nDie Offiziere melden sich so schnell wie möglich bei dir.",
            color=discord.Color.from_rgb(100, 100, 200)
        )
        await interaction.channel.send(embed=embed, view=KummerkastenButton())
        await interaction.response.send_message("Kummerkasten-Embed wurde gepostet!", ephemeral=True)

    async def cog_load(self):
        self.bot.add_view(KummerkastenButton())
        self.bot.add_view(TicketSchliessenView())


async def setup(bot):
    await bot.add_cog(KummerkastenCog(bot))