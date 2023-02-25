import logging

import discord
import discord.ext.commands as commands
from discord import app_commands

from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.messaging.events import Events
from bot.modals.class_modal import AddClassModal, valid_course_num, valid_course_maj
from bot.sock_bot import SockBot
from bot.utils.helpers import as_timestamp, error_embed

log = logging.getLogger(__name__)


class ManageClassesCog(commands.GroupCog, name='class'):

    def __init__(self, bot: SockBot):
        self.bot = bot
        self.repo = ClassRepository()

    @app_commands.command(name='add', description='Add a class channel.')
    async def add(self, inter: discord.Interaction, prefix: str | None = None, course_number: int | None = None):
        # check if a current semester exists
        if not await self.repo.get_current_semester():
            embed = discord.Embed(title='📔 No Current Semester', color=Colors.Error)
            embed.description = 'Could not create class: there is no current semester in session.\n' \
                                'Here is the information for the next upcoming semester.'
            next_semester = await self.repo.get_next_semester()
            embed.add_field(name='Next Semester', value=next_semester.semester_name)
            embed.add_field(name='Start Date', value=as_timestamp(next_semester.start_date))
            await inter.response.send_message(embed=embed)
            return

        # validate our given prefix and course number, if given
        if prefix and not valid_course_maj(prefix):
            embed = error_embed(inter.user, f'The given course prefix `{prefix}` is invalid.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        if course_number and not valid_course_num(course_number):
            embed = error_embed(inter.user, f'The given course number `{course_number}` is invalid.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        await inter.response.send_modal(AddClassModal(self.bot, class_data=(prefix, course_number)))

    @app_commands.command(name='insert', description='Insert a class channel.')
    @app_commands.checks.has_permissions(administrator=True)
    async def insert(self, inter: discord.Interaction, channel: discord.TextChannel, role: discord.Role | None = None):
        # check if a current semester exists
        if not await self.repo.get_current_semester():
            embed = discord.Embed(title='📔 No Current Semester', color=Colors.Error)
            embed.description = 'Could not insert class: there is no current semester in session.\n' \
                                'Here is the information for the next upcoming semester.'
            next_semester = await self.repo.get_next_semester()
            embed.add_field(name='Next Semester', value=next_semester.semester_name)
            embed.add_field(name='Start Date', value=as_timestamp(next_semester.start_date))
            await inter.response.send_message(embed=embed)
            return

        # check to see if the given channel is already in the repo
        if await self.repo.search_class_by_channel(channel):
            embed = error_embed(inter.user, f'The given channel {channel.mention} is already registered.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        await inter.response.send_modal(AddClassModal(self.bot, channel=channel, role=role))

    @app_commands.command(name='archive', description='Manually archive a class channel.')
    @app_commands.checks.has_permissions(administrator=True)
    async def class_archive(self, inter: discord.Interaction, channel: discord.TextChannel):
        # make sure that the given channel is a class channel
        if not (class_channel := await self.repo.search_class_by_channel(channel.id)):
            embed = error_embed(inter.user, f'Channel {channel.mention} is not registered as a class.')
            await inter.response.send_message(embed=embed)
            return

        # make sure if it is a class channel, that it is not already archived
        if class_channel.class_archived:
            embed = error_embed(inter.user, f'Channel {channel.mention} is already archived.')
            await inter.response.send_message(embed=embed)
            return

        await self.bot.messenger.publish(Events.on_class_archive, class_channel, inter)

    @app_commands.command(name='unarchive', description='Manually unarchive a class channel.')
    @app_commands.checks.has_permissions(administrator=True)
    async def class_unarchive(self, inter: discord.Interaction, channel: discord.TextChannel):
        # make sure that the given channel is a class channel
        if not (class_channel := await self.repo.search_class_by_channel(channel.id)):
            embed = error_embed(inter.user, f'Channel {channel.mention} is not registered as a class.')
            await inter.response.send_message(embed=embed)
            return

        # make sure that if it is a class channel, that it is archived
        if not class_channel.class_archived:
            embed = error_embed(inter.user, f'Channel {channel.mention} is not archived.')
            await inter.response.send_message(embed=embed)
            return

        # make sure that a current semester exists!
        if not await self.repo.get_current_semester():
            embed = error_embed(inter.user, 'There is no current semester in session.')
            await inter.response.send_message(embed=embed)
            return

        await self.bot.messenger.publish(Events.on_class_unarchive, inter, class_channel)

    @app_commands.command(name='info', description='Get the class information of a channel.')
    async def info(self, inter: discord.Interaction, channel: discord.TextChannel):
        # check to make sure the given channel is a class channel
        if not (class_channel := await self.repo.search_class_by_channel(channel.id)):
            embed = discord.Embed(title='📔 Class Not Found', color=Colors.Purple)
            embed.description = f'Channel {channel.mention} is not registered as a class.'
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # fetch the role and the semester of this class (semester should NEVER be None)
        role = self.bot.guild.get_role(class_channel.class_role_id)
        semester = await self.repo.search_semester(class_channel.semester_id)
        assert semester is not None

        # send the embed with the class details
        embed = discord.Embed(title='📔 Class Details', color=Colors.Purple)
        embed.description = f'The channel {channel.mention} is registered as a class.'
        embed.add_field(name='Class Title', value=class_channel.full_title, inline=False)
        embed.add_field(name='Class Role', value=role.mention if role else 'None')
        embed.add_field(name='Class Semester', value=semester.semester_name)
        embed.add_field(name='Archived', value=bool(class_channel.class_archived))

        await inter.response.send_message(embed=embed)

    semester_group = app_commands.Group(name='semester', description='Manage or list a semester.')

    @semester_group.command(name='list', description='Get info on the current or next semester.')
    async def list(self, inter: discord.Interaction):
        # check if we are currently in a semester
        if current_semester := await self.repo.get_current_semester():
            embed = discord.Embed(title='📔 Current Semester', color=Colors.Purple)
            embed.description = 'Here is the information for the current semester.'
            embed.add_field(name='Name', value=current_semester.semester_name, inline=False)
            embed.add_field(name='Start Date', value=as_timestamp(current_semester.start_date))
            embed.add_field(name='End Date', value=as_timestamp(current_semester.end_date))
            embed.set_footer(text='Start and end dates do not reflect the actual start and end of a semester.')
            await inter.response.send_message(embed=embed)

        # if no current semester, try and fetch the next one
        elif next_semester := await self.repo.get_next_semester():
            embed = discord.Embed(title='📔 Next Semester', color=Colors.Purple)
            embed.description = 'Currently, there is no semester in session.\n' \
                                'Here is the information for the upcoming semester.'
            embed.add_field(name='Name', value=next_semester.semester_name)
            embed.add_field(name='Start Date', value=as_timestamp(next_semester.start_date))
            embed.set_footer(text='Start and end dates do not reflect the actual start and end of a semester.')
            await inter.response.send_message(embed=embed)

        # worst case scenario...
        else:
            embed = error_embed(inter.user, 'Could not find current nor next semester.')
            await inter.response.send_message(embed=embed)

    @semester_group.command(name='archive', description='Manually archive a semester.')
    @app_commands.checks.has_permissions(administrator=True)
    async def semester_archive(self, inter: discord.Interaction, semester_id: str):
        # check if the semester id is valid and the semester exists
        if not (semester := await self.repo.search_semester(semester_id)):
            embed = error_embed(inter.user, f'A semester with the ID `{semester_id}` does not exist.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # make sure there are class channels to archive for that semester
        if len(await self.repo.get_semester_classes(semester)) == 0:
            embed = error_embed(inter.user, f'No unarchived classes for semester {semester.semester_name}.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        await self.bot.messenger.publish(Events.on_semester_archive, semester, inter)


async def setup(bot: SockBot) -> None:
    await bot.add_cog(ManageClassesCog(bot))
