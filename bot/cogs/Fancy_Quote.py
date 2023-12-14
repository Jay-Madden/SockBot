import logging
import discord
import discord.ext.commands as commands
import bot.extensions as ext
from bot.consts import Colors

log = logging.getLogger(__name__)


class FancyQuoteCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self._last_member: discord.Member | None = None

    @ext.command()
    @ext.long_help(
        "Creates a fancy quote based on the given message with the author either being given or being the username")
    @ext.short_help("Creates a fancy quote from the given value")
    @ext.example(
        (
                "fancy_quote @<Author Name> <Quote String>",
                "fancy_quote <Author Name> <Quote String>"
        )
    )
    async def fancy_quote(self, ctx, member: discord.Member | str, *, quote: str) -> None:

        error_title = ""
        error_message = ""

        if member is None:
            error_title = "Missing member argument"
            error_message = f"Invalid argument(s): Missing member value. See `{await self.bot.current_prefix(ctx)}help fancy_quote` for info."
        elif quote is None:
            error_title = "Missing quote argument"
            error_message = f"Invalid argument(s): Missing quote value. See `{await self.bot.current_prefix(ctx)}help fancy_quote` for info."
        if error_title != "":
            embed = discord.Embed(title="Fancy_Quote", color=Colors.Error)
            embed.add_field(name="ERROR: " + error_title, value=error_message, inline=False)
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="",
            color=Colors.Purple,
        )
        embed.add_field(
            name="",
            value=f"\"*{quote}*\"",
            inline=False,
        )
        embed.set_footer(text=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        if isinstance(member, discord.Member):
            embed.title = f"{member.nick}"
            embed.set_thumbnail(url=member.display_avatar.url)
        else:
            embed.title = member
        await ctx.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(FancyQuoteCog(bot))
