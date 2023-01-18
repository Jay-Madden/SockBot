import asyncio
import logging
from dataclasses import dataclass

import discord
import discord.ext.commands as commands
from discord import app_commands

import bot.extensions as ext
from bot.consts import Colors, Staff
from bot.data.class_repository import ClassRepository
from bot.messaging.events import Events
from bot.modals.class_modal import AddClassModal
from bot.sock_bot import SockBot
from bot.utils.helpers import as_timestamp, error_embed
from bot.utils.user_choice import UserChoice

log = logging.getLogger(__name__)
TIMEOUT = 60


@dataclass
class ClassType:
    _abbv: str | None = None

    @property
    def abbv(self) -> str | None:
        return self._abbv

    @abbv.setter
    def abbv(self, val: str) -> None:
        self._abbv = val.lower()

    _teacher: str | None = None

    @property
    def teacher(self) -> str | None:
        return self._teacher

    @teacher.setter
    def teacher(self, val: str) -> None:
        self._teacher = val.lower()

    number = 0
    name: str | None = None
    description: str | None = None

    @property
    def channel(self) -> str:
        empty = ""
        teacher = f'{f"-{self.teacher}" if self.teacher else empty}'
        return f"{self.abbv}-{self.number}{teacher}"

    @property
    def category(self) -> str:
        return f"{self.abbv} {round_down(self.number, 1000)} levels"

    @property
    def role(self) -> str:
        return f"{self.abbv}-{self.number}"

    def __str__(self) -> str:
        return f"""
        Class Major: **{self.abbv}**
        Class Number: ** {self.number}**
        Class Name: ** {self.name}**
        Class Description: ** {self.description}**
        Class Professor: ** {self.teacher}**
        """


class ManageClassesCog(commands.GroupCog, name='class'):

    def __init__(self, bot: SockBot):
        self.bot = bot
        self.repo = ClassRepository()

    @app_commands.command(name='add', description='Add a class channel.')
    async def add(self, inter: discord.Interaction, prefix: str | None = None, course_number: int | None = None):
        if not await self.repo.get_current_semester():
            embed = discord.Embed(title='No Current Semester', color=Colors.Error)
            embed.description = 'Could not create class: there is no current semester in session.\n' \
                                'Here is the information for the next upcoming semester.'
            next_semester = await self.repo.get_next_semester()
            embed.add_field(name='Next Semester', value=next_semester.semester_name)
            embed.add_field(name='Start Date', value=as_timestamp(next_semester.start_date()))
            await inter.response.send_message(embed=embed)
            return
        if prefix and not 3 <= len(prefix) <= 4:
            embed = error_embed(inter.user, f'The given course prefix `{prefix}` is invalid.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        if course_number and not 1000 <= course_number <= 8999:
            embed = error_embed(inter.user, f'The given course number `{course_number}` is invalid.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        await inter.response.send_modal(AddClassModal(class_data=(prefix, course_number)))

    @app_commands.command(name='insert', description='Insert a class channel.')
    async def insert(self, inter: discord.Interaction, channel: discord.TextChannel):
        if not await self._perms_check(inter):
            return
        if not await self.repo.get_current_semester():
            embed = discord.Embed(title='No Current Semester', color=Colors.Error)
            embed.description = 'Could not insert class: there is no current semester in session.\n' \
                                'Here is the information for the next upcoming semester.'
            next_semester = await self.repo.get_next_semester()
            embed.add_field(name='Next Semester', value=next_semester.semester_name)
            embed.add_field(name='Start Date', value=as_timestamp(next_semester.start_date()))
            await inter.response.send_message(embed=embed)
            return
        if await self.repo.search_class_by_channel(channel):
            embed = error_embed(inter.user, f'The given channel {channel.mention} is already registered.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        await inter.response.send_modal(AddClassModal(channel=channel))

    semester_group = app_commands.Group(name='semester', description='Manage or list a semester.')

    @semester_group.command(name='list', description='Get info on the current or next semester.')
    async def list(self, inter: discord.Interaction):
        current_semester = await self.repo.get_current_semester()
        next_semester = await self.repo.get_next_semester()
        if current_semester:
            embed = discord.Embed(title='📔 Current Semester', color=Colors.Purple)
            embed.description = 'Here is the information for the current semester.'
            embed.add_field(name='Name', value=current_semester.semester_name, inline=False)
            embed.add_field(name='Start Date', value=as_timestamp(current_semester.start_date()))
            embed.add_field(name='End Date', value=as_timestamp(current_semester.end_date()))
            embed.set_footer(text='Start and end dates do not reflect the actual start and end of a semester.')
            await inter.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title='📔 Next Semester', color=Colors.Purple)
            embed.description = 'Currently, there is no semester in session.\n' \
                                'Here is the information for the upcoming semester.'
            embed.add_field(name='Name', value=next_semester.semester_name)
            embed.add_field(name='Start Date', value=as_timestamp(next_semester.start_date()))
            embed.set_footer(text='Start and end dates do not reflect the actual start and end of a semester.')
            await inter.response.send_message(embed=embed)

    @semester_group.command(name='archive', description='Manually archive a semester.')
    async def semester_archive(self, inter: discord.Interaction, semester_id: str):
        if not await self._perms_check(inter):
            return
        if not (semester := await self.repo.search_semester(semester_id)):
            embed = error_embed(inter.user, f'A semester with the ID `{semester_id}` does not exist.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        await self.bot.messenger.publish(Events.on_semester_archive, inter, semester)

    @app_commands.command(name='archive', description='Manually archive a class channel.')
    async def class_archive(self, inter: discord.Interaction, channel: discord.TextChannel):
        if not await self._perms_check(inter):
            return
        if not (class_channel := await self.repo.search_class_by_channel(channel.id)):
            embed = error_embed(inter.user, f'Channel {channel.mention} is not registered as a class.')
            await inter.response.send_message(embed=embed)
            return
        await self.bot.messenger.publish(Events.on_class_archive, inter, class_channel)

    @app_commands.command(name='info', description='Get the class information of a channel.')
    async def info(self, inter: discord.Interaction, channel: discord.TextChannel):
        if not (class_channel := await self.repo.search_class_by_channel(channel.id)):
            embed = discord.Embed(title='Class Not Found', color=Colors.Purple)
            embed.description = f'Channel {channel.mention} is not registered as a class.'
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(title='📔 Class Details', color=Colors.Purple)
        embed.description = f'The channel {channel.mention} is registered as a class.'
        embed.add_field(name='Class Name', value=class_channel.class_name)
        embed.add_field(name='Class Code', value=class_channel.class_code())
        embed.add_field(name='Class Instructor', value=class_channel.class_professor.title())
        embed.add_field(name='Class Semester', value=class_channel.semester_id)
        embed.add_field(name='Archived', value=class_channel.class_archived)
        await inter.response.send_message(embed=embed)

    async def _perms_check(self, inter: discord.Interaction) -> bool:
        if not Staff.is_staff(inter.user):
            embed = error_embed(inter.user, 'You do not have the correct permissions to run this command.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @ext.group(pass_context=True, aliases=["class"], case_insensitive=True)
    @ext.long_help("Command group for the manage classes functionality")
    @ext.short_help("Academic class creation functionality")
    async def classes(self, ctx) -> None:
        pass

    # @classes.command(pass_context=True, aliases=["create"])
    # @ext.long_help(
    #     "Command to initiate the new class creation wizard, optionally takes a "
    #     'class name as a parameter E.G "cpsc-1010"'
    # )
    # @ext.short_help("Starts the class creation wizard")
    # @ext.example(("class add", "class add cpsc-1010"))
    # async def add(self, ctx, class_name: str | None = None) -> None:
    #     """
    #     Command to initiate the new class creation wizard, optionally takes a
    #     class name as a parameter E.G "cpsc-1010"
    #
    #     Args:
    #         class_name (str, optional): Formatted class abbreviation and number
    #         E.G "cpsc-1010" Defaults to None.
    #     """
    #
    #     class_repr: ClassType | None = ClassType()
    #
    #     assert class_repr
    #     if class_name:
    #         # try to parse the class name given, if its not in the correct format split will throw
    #         abbv, num = class_name.split("-")
    #         class_repr.abbv = abbv
    #         class_repr.number = int(num)
    #
    #     # get the user class input and store it in the dataclass
    #     class_repr = await self.input_class(ctx, class_repr=class_repr)
    #     if not class_repr:
    #         return
    #
    #     try:
    #         # attempt to get the category to add the class too
    #         category: discord.CategoryChannel | None = (
    #             await commands.converter.CategoryChannelConverter().convert(
    #                 ctx, class_repr.category
    #             )
    #         )
    #     except:
    #         # the category wasnt found, ask if we want to create one
    #         log.info(
    #             f"Class creation category {class_repr.category} non existent, Create a new one?"
    #         )
    #         category = await self.create_category(ctx, class_repr)
    #
    #         # Finding the category and creating one failed
    #     # We cant do anything more, bail out early
    #     if not category:
    #         embed = discord.Embed(
    #             title=f"Error: Category {class_repr.category} not found and not created, Exiting Wizard",
    #             color=Colors.Error,
    #         )
    #         await ctx.send(embed=embed)
    #         return
    #
    #     # Create the class channel in the given category
    #     channel = await self.create_channel(category, class_repr)
    #     await channel.send(f"Here is your generated class channel {ctx.author.mention}, Good luck!")
    #
    #     # create a class role and mark it as assignable
    #     role = await self.create_role(ctx, class_repr)
    #
    #     # Sleep here to make sure the role has been sent to the database and added
    #     await asyncio.sleep(0.5)
    #     msg = await ctx.send(f'!role add {role.id}')
    #     await msg.delete(delay=1)
    #
    #     # sync perms with cleanup role
    #     await self.sync_perms(ctx, channel, role)

    async def input_class(self, ctx, class_repr: ClassType) -> ClassType | None:
        def input_check(msg: discord.Message) -> bool:
            return msg.author == ctx.author and ctx.channel == msg.channel

        # check if the initial command contained a class abbv and number
        if not class_repr.abbv:
            embed = discord.Embed(
                title="**New class setup wizard started :white_check_mark:**",
                color=Colors.Purple,
            )
            avi = ctx.author.display_avatar.url
            embed.set_footer(text=f"{ctx.author} - Time Limit: {TIMEOUT} Seconds", icon_url=avi)
            embed.add_field(name="**Current values**", value=class_repr)
            embed.add_field(
                name="Please enter the class abbreviation and name E.G.",
                value="cpsc-1010",
                inline=False,
            )

            await ctx.send(embed=embed)

            try:
                msg = await self.bot.wait_for("message", timeout=TIMEOUT, check=input_check)
                abbv, number = msg.content.split("-")
                class_repr.abbv = abbv
                class_repr.number = int(number)
            except asyncio.TimeoutError:
                await self.input_timeout(ctx)
                return None
        else:
            embed = discord.Embed(
                title="**New class setup wizard started :white_check_mark:**",
                color=Colors.Purple,
            )
            await ctx.send(embed=embed)

        embed = discord.Embed(
            title=f'Class "{class_repr.abbv}-{class_repr.number}" set', color=Colors.Purple
        )
        avi = ctx.author.display_avatar.url
        embed.set_footer(text=f"{ctx.author} - Time Limit: {TIMEOUT} Seconds", icon_url=avi)
        embed.add_field(name="**Current values**", value=class_repr)
        embed.add_field(
            name='Please enter the class name or "None" to skip this step E.G.',
            value="Introduction to C",
            inline=False,
        )

        await ctx.send(embed=embed)

        try:
            val = (await self.bot.wait_for("message", timeout=TIMEOUT, check=input_check)).content
            if val != "None":
                class_repr.name = val
        except asyncio.TimeoutError:
            await self.input_timeout(ctx)
            return None

        embed = discord.Embed(
            title=f'Class name: "{class_repr.name}" set', color=Colors.Purple
        )
        avi = ctx.author.display_avatar.url
        embed.set_footer(text=f"{ctx.author} - Time Limit: {TIMEOUT} Seconds", icon_url=avi)
        embed.add_field(name="**Current values**", value=class_repr)
        embed.add_field(
            name='Please enter the class description (must be less than 256 characters) or "None" to skip this step E.G.',
            value="An overview of programming fundamentals using the C programming langauge",
            inline=False,
        )

        await ctx.send(embed=embed)

        try:
            # Keep retrying to get the description until we get a less then 256 characters one or the wait times out
            while (
                len(
                    val := (
                        await self.bot.wait_for("message", timeout=TIMEOUT, check=input_check)
                    ).content
                )
            ) > 255:
                await ctx.send(
                    "Error: Description needs to be less than 256 characters\nPlease try again"
                )
            if val != "None":
                class_repr.description = val
        except asyncio.TimeoutError:
            await self.input_timeout(ctx)
            return None

        embed = discord.Embed(
            title=f'Class description: "{class_repr.description}" set', color=Colors.Purple
        )
        avi = ctx.author.display_avatar.url
        embed.set_footer(text=f"{ctx.author} - Time Limit: {TIMEOUT} Seconds", icon_url=avi)
        embed.add_field(name="**Current values**", value=class_repr)
        embed.add_field(
            name='Please enter the class professors last name or "None" to skip this step E.G.',
            value="Plis",
            inline=False,
        )

        await ctx.send(embed=embed)

        try:
            val = (await self.bot.wait_for("message", timeout=TIMEOUT, check=input_check)).content
            if val != "None":
                class_repr.teacher = val
        except asyncio.TimeoutError:
            await self.input_timeout(ctx)
            return None

        embed = discord.Embed(
            title=f'Class and role "{class_repr.role}" created in category "{class_repr.category}" ',
            color=Colors.Purple,
        )
        embed.add_field(name="**Current values**", value=class_repr)
        await ctx.send(embed=embed)

        return class_repr

    async def create_category(
        self, ctx, class_repr: ClassType
    ) -> discord.CategoryChannel | None:
        get_input = UserChoice(ctx=ctx, timeout=TIMEOUT)
        choice = await get_input.send_confirmation(
            content=f"""
            Error: Category "{class_repr.category}" not found
            Would you like to create it?
            """,
            is_error=True,
        )

        if not choice:
            return None

        log.info(f'Creating category "{class_repr.category}" in guild: "{ctx.guild.name}"')
        return await ctx.guild.create_category(class_repr.category)

    async def create_channel(
        self, category: discord.CategoryChannel, class_repr: ClassType
    ) -> discord.TextChannel:
        log.info(f'Creating new Class channel "{class_repr.name}""')
        return await category.create_text_channel(
            class_repr.channel, topic=f"{class_repr.name} - {class_repr.description}"
        )

    async def create_role(self, ctx, class_repr: ClassType) -> discord.Role:
        log.info(f'Creating new class role "{class_repr.role}""')
        # Attempt to convert the role, if we cant then we create a new one
        try:
            role = await commands.converter.RoleConverter().convert(ctx, class_repr.role)
        except:
            role = await ctx.guild.create_role(name=class_repr.role, mentionable=False)

        try:
            # wait a split second to insert the role in the db
            await asyncio.sleep(0.25)
            await self.bot.messenger.publish(Events.on_assignable_role_add, role)
        except:
            # If the marking of the role as assignable fails
            # Wait a second for the api to finish inserting the role then try it again
            await asyncio.sleep(1)
            await self.bot.messenger.publish(Events.on_assignable_role_add, role)

        return role

    async def sync_perms(
        self, ctx, channel: discord.TextChannel, role: discord.Role
    ) -> None:
        # Check if cleanup role exists
        if not (cleanup := discord.utils.get(ctx.guild.roles, name="Cleanup")):
            cleanup = await ctx.guild.create_role(name="Cleanup", mentionable=False)

            assert cleanup

            await self.bot.messenger.publish(Events.on_assignable_role_add, cleanup)

            # Upon detecting first time user, show embed showing how to use commands
            embed = discord.Embed(
                title="Welcome to SockBot class management!", color=Colors.Purple
            )
            embed.add_field(
                name="To assign your class year or a specific class, run the command:",
                value="```!roles <year>``` or ```!roles cpsc-<class-number>```",
                inline=False,
            )
            embed.add_field(
                name="To see a list of assignable roles run:", value="```!roles```", inline=False
            )
            embed.add_field(
                name="If you would like to hide all class channels you are not in, run:",
                value="```!roles cleanup```",
                inline=False,
            )
            await ctx.send(embed=embed)

        log.info("Syncing channel and role with cleanup")
        await channel.set_permissions(role, view_channel=True)
        await channel.set_permissions(cleanup, view_channel=False)
        await role.edit(position=2)

        await cleanup.edit(position=1)

    @classes.command(pass_context=True, aliases=["delete"])
    @commands.has_guild_permissions(administrator=True)
    async def archive(self, ctx, channel: discord.TextChannel) -> None:
        pass

    async def input_timeout(self, ctx) -> None:
        await ctx.send("Response timed out please redo the class wizard")


def round_down(num: int, divisor: int) -> int:
    return num - (num % divisor)


async def setup(bot: SockBot) -> None:
    await bot.add_cog(ManageClassesCog(bot))
