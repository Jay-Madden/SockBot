import logging
from datetime import timedelta, datetime
from enum import Enum
from typing import Optional

import discord
from discord.ext import commands, tasks

import bot.extensions as ext
from bot import bot_secrets
from bot.consts import Colors
from bot.data.birthday_repository import BirthdayRepository
from bot.models.birthday_model import Birthday
from bot.utils.helpers import strtodt, error_embed

log = logging.getLogger(__name__)


class AnnouncementMode(Enum):
    DM_ONLY = 0
    CHANNEL_ONLY = 1
    DM_AND_CHANNEL = 2


class BirthdayCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.repo = BirthdayRepository()
        self.birthday_role: Optional[int] = bot_secrets.secrets.birthday_role_id
        self.cooldown = timedelta(days=bot_secrets.secrets.birthday_cooldown_in_days)
        self.birthday_channel: Optional[int] = bot_secrets.secrets.birthday_channel_id
        self.announcement_mode: AnnouncementMode = AnnouncementMode(bot_secrets.secrets.birthday_announcement_mode)
        self.check_birthdays.start()

    def cog_unload(self) -> None:
        self.check_birthdays.cancel()

    def get_birthday_this_year(self, birthday: Birthday):
        return datetime.strptime(f"{birthday.month} {birthday.day} {datetime.now().year}", "%m %d %Y")

    def get_age(self, birthday: Birthday):
        birthday_this_year = self.get_birthday_this_year(birthday)
        full_birthday = datetime.strptime(f"{birthday.month} {birthday.day} {birthday.year}", "%m %d %Y")
        return (birthday_this_year - full_birthday).days // 365

    def get_ordinal_suffix(self, day: int) -> str:
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th') if day not in (11, 12, 13) else 'th'

    @tasks.loop(seconds=86400)
    async def check_birthdays(self):
        if len(self.bot.guilds) == 0:
            self.check_birthdays.restart()
            return
        today = datetime.now()
        birthdays = await self.repo.get_todays_birthdays()
        guild = self.bot.guilds[0]
        birthday_role = [role for role in await guild.fetch_roles() if role.id == self.birthday_role][0]
        for non_birthday in await self.repo.get_non_birthdays():
            member: discord.Member = await guild.fetch_member(non_birthday.member_id)
            await member.remove_roles(birthday_role, reason="No longer birthday")

        for birthday in birthdays:
            if not birthday.last_congratulated or True or today - datetime.fromisoformat(
                    birthday.last_congratulated.split('.')[0]) > timedelta(hours=24):
                age_format = ' '
                if birthday.year:
                    age = self.get_age(birthday)
                    age_format = f" {age}{self.get_ordinal_suffix(age)} "
                member: discord.Member = await guild.fetch_member(birthday.member_id)
                embed = discord.Embed(color=Colors.Purple, title="⭐ WE HAVE A BIRTHDAY! ⭐",
                                      description=f"The Clemson CPSC discord wants to wish you a very happy{age_format}birthday today, {str(member)}!")

                if member.avatar:
                    embed.set_footer(text=str(member), icon_url=member.avatar.url)
                    embed.set_thumbnail(url=member.avatar.url)
                if self.announcement_mode == AnnouncementMode.CHANNEL_ONLY or self.announcement_mode == AnnouncementMode.DM_AND_CHANNEL:
                    channel = await self.bot.fetch_channel(self.birthday_channel)
                    await channel.send(embed=embed)
                if self.announcement_mode == AnnouncementMode.DM_ONLY or self.announcement_mode == AnnouncementMode.DM_AND_CHANNEL:
                    await member.send(embed=embed)
                if self.birthday_role:
                    await member.add_roles(birthday_role, reason="It is their birthday")
                await self.repo.update_last_congratulated(birthday.member_id)

    @ext.group(case_insensitive=True,
               aliases=["bd"])
    @ext.long_help('Commands for managing member birthdays.')
    @ext.short_help('birthday commands')
    @ext.example('birthday set')
    async def birthday(self, ctx: commands.Context, target: Optional[discord.Member]):
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command('birthday view'), target=target)

    @birthday.command(aliases=['view'])
    @ext.long_help('View birthday for a user. Provide no arguments to view your own set birthday.')
    @ext.short_help('view birthdays')
    @ext.example(('birthday view', 'birthday view @SockBot'))
    async def view_birthday(self, ctx: commands.Context, target: Optional[discord.Member] = None):
        if not target:
            target = ctx.author
        birthday = await self.repo.get_birthday(target.id)
        embed = discord.Embed(color=Colors.Error if not birthday else Colors.Purple, title='⭐ Birthday ⭐')
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
            embed.set_footer(text=f"Command called by {ctx.author.name}", icon_url=ctx.author.avatar.url)
        if not birthday:
            embed.add_field(name='No Birthday Found',
                            value=f"The user '{target.name}' does not have a birthday set in the bot.")
        else:

            message = f"{target.name} has a birthday on {birthday.month}/{birthday.day}! "
            if birthday.year:
                message += f"(They {'will be turning' if self.get_birthday_this_year(birthday) > datetime.now() else 'turned'} {self.get_age(birthday)} this year!)"
            embed.add_field(name='Member Birthday', value=message)
        await ctx.send(embed=embed)

    @birthday.command(aliases=['set', 'add'])
    @ext.long_help(
        'Set your birthday in the bot. Either full month names or month numbers are valid.'
    )
    @ext.short_help('Set your birthday')
    @ext.example(('birthday 11 9', 'birthday november 9', 'birthday 11 9 2000'))
    async def set_birthday(self, ctx: commands.Context, month: int | str, day: int, year: Optional[int]):
        if isinstance(month, str):
            for format in ["%B", "%b"]:
                try:
                    month = datetime.strptime(format, month.lower()).month
                except ValueError:
                    pass
            if not isinstance(month, int):
                await ctx.send(embed=error_embed(ctx.author, description=f"Invalid month."))
                return
        try:
            if year:
                datetime.strptime(f"{month} {day} {year}", "%m %d %Y")
            else:
                datetime.strptime(f"{month} {day}", "%m %d")
        except ValueError:
            await ctx.send(embed=error_embed(ctx.author, description=f"Invalid day or year."))
            return
        existing = await self.repo.get_birthday(ctx.author.id)
        if existing:
            existing.last_used = strtodt(existing.last_used.split('.')[0])
            cmd_valid = existing.last_used + self.cooldown
            if cmd_valid < datetime.now():
                await self.repo.update_birthday(ctx.author.id, month, day, year)
            else:
                await ctx.send(embed=error_embed(ctx.author,
                                                 description=f"You are on cooldown. You can use this command again in {(cmd_valid - datetime.now()).days} days."))
                return
        else:
            await self.repo.add_birthday(ctx.author.id, month, day, year)

        embed = discord.Embed(color=Colors.Purple, title='⭐ Birthday Updated ⭐',
                              description=f"Successfully changed birthday to {month}/{day}{'/' + str(year) if year else ''}!")
        if ctx.author.avatar:
            embed.set_thumbnail(url=ctx.author.avatar.url)
            embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)


async def setup(bot):
    cog = BirthdayCog(bot)
    await bot.add_cog(cog)
