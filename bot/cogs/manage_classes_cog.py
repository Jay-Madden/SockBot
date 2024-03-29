import logging

import discord
import discord.ext.commands as commands
from discord import app_commands

from bot.consts import Colors, Staff
from bot.data.class_repository import ClassRepository
from bot.messaging.events import Events
from bot.modals.class_modal import ClassModal, valid_course_num, valid_course_maj, INSERT, EDIT
from bot.modals.ta_modal import TAModal
from bot.models.class_models import ClassTA
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

        await inter.response.send_modal(
            ClassModal(self.bot, class_data=(prefix, course_number))
        )

    @app_commands.command(name='insert', description='Insert a class channel.')
    @app_commands.checks.has_permissions(administrator=True)
    async def insert(self,
                     inter: discord.Interaction,
                     channel: discord.TextChannel,
                     role: discord.Role | None = None,
                     archive: bool = True):
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

        await inter.response.send_modal(
            ClassModal(self.bot, mode=INSERT, class_data=(channel, role, archive))
        )

    @app_commands.command(name='edit', description='Edit a class channel.')
    @app_commands.checks.has_permissions(administrator=True)
    async def edit(self, inter: discord.Interaction, channel: discord.TextChannel, role: discord.Role | None = None):
        if not await self.repo.search_class_by_channel(channel):
            embed = error_embed(inter.user, f'The given channel {channel.mention} is not a class channel.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        await inter.response.send_modal(
            ClassModal(self.bot, mode=EDIT, class_data=(channel, role, False))
        )

    @app_commands.command(name='role', description='Add or remove a class role from yourself.')
    async def role(self, inter: discord.Interaction, role: discord.Role):
        if not await self.repo.search_class_by_role(role):
            embed = error_embed(inter.user, f'The given role {role.mention} is not a class role.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        has_role = inter.user.get_role(role.id) is not None

        embed = discord.Embed(title=f"📔 Class Role {'Removed' if has_role else 'Added'}", color=Colors.Purple)
        embed.add_field(name='Role', value=f"{role.mention} {':arrow_left:' if has_role else ':arrow_right:'}")
        embed.add_field(name='User', value=inter.user.mention)
        if has_role:
            await inter.user.remove_roles(role, reason='User requested role removed')
        else:
            await inter.user.add_roles(role, reason='User requested role')

        await inter.response.send_message(embed=embed)

    @app_commands.command(name='cleanup', description='Add or remove the cleanup role from yourself.')
    async def cleanup(self, inter: discord.Interaction):
        cleanup_role: discord.Role | None = None
        for role in self.bot.guild.roles:
            if role.name == 'Cleanup':
                cleanup_role = role
                break

        if not cleanup_role:
            cleanup_role = await self.bot.guild.create_role(name='Cleanup', reason='Cleanup role not found.')

        has_role = inter.user.get_role(cleanup_role.id)

        embed = discord.Embed(title=f"📔 Cleanup Role {'Removed' if has_role else 'Added'}", color=Colors.Purple)
        embed.add_field(name='Role', value=f"{cleanup_role.mention} {':arrow_left:' if has_role else ':arrow_right:'}")
        embed.add_field(name='User', value=inter.user.mention)
        if has_role:
            await inter.user.remove_roles(cleanup_role, reason='Cleanup role removal requested')
        else:
            await inter.user.add_roles(cleanup_role, reason='Cleanup role addition requested')

        await inter.response.send_message(embed=embed)

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
    async def class_info(self, inter: discord.Interaction, channel: discord.TextChannel):
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

    @semester_group.command(name='info', description='Get info on the current or next semester.')
    async def semester_info(self, inter: discord.Interaction):
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

    ta_group = app_commands.Group(name='ta', description='Manage or list class teacher assistants.')

    @ta_group.command(name='add', description='Add a TA to a class.')
    @app_commands.checks.has_permissions(administrator=True)
    async def ta_add(self,
                     inter: discord.Interaction,
                     member: discord.Member,
                     channel: discord.TextChannel,
                     apply_role: bool = True):
        # check if the given discord channel is a class channel
        if not (clazz := await self.repo.search_class_by_channel(channel)):
            embed = error_embed(inter.user, f'The channel {channel.mention} is not a class channel.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # check to make sure the given member is not already a TA
        if await self.repo.get_ta(member.id, channel.id):
            embed = error_embed(inter.user, f'{member.mention} is already a TA for {channel.mention}.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # create/apply the role if needed
        role: discord.Role | None = None
        if apply_role:
            if not clazz.class_ta_role_id or not (role := self.bot.guild.get_role(clazz.class_ta_role_id)):
                if not (role := self._find_role(clazz.ta_role_name)):
                    role = await self.bot.guild.create_role(name=clazz.ta_role_name, color=discord.Color.yellow())
                clazz.class_ta_role_id = role.id
                await self.repo.update_class(clazz)
            await member.add_roles(role, reason=f'Approved by {str(inter.user)}')

        # create our ClassTA model, insert it into the repo, and send the embed
        class_ta = ClassTA(channel_id=channel.id, ta_user_id=member.id, ta_display_tag=apply_role, ta_details=None)
        await self.repo.insert_ta(class_ta)
        embed = discord.Embed(title='📔 Class TA Added', color=Colors.Purple)
        if role and apply_role:
            embed.description = f'The role {role.mention} was applied.'
        embed.add_field(name='Class', value=clazz.full_title, inline=False)
        embed.add_field(name='Channel', value=channel.mention)
        embed.add_field(name='User', value=member.mention)
        await inter.response.send_message(embed=embed)

    @ta_group.command(name='remove', description='Remove a TA from a class.')
    @app_commands.checks.has_permissions(administrator=True)
    async def ta_remove(self,
                        inter: discord.Interaction,
                        member: discord.Member,
                        channel: discord.TextChannel | None = None):
        # check if the given discord channel is a class channel
        if channel and not await self.repo.search_class_by_channel(channel):
            embed = error_embed(inter.user, f'The channel {channel.mention} is not a class channel.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # get all ClassTA models the user is in
        class_tas: list[ClassTA]
        if channel:
            class_tas = [await self.repo.get_ta(member, channel)]
        else:
            class_tas = await self.repo.get_tas_by_user(member)
        if not len(class_tas) or not all(class_tas):
            embed = error_embed(inter.user,
                                f'The user {member.mention} is not a TA{f" for {channel.mention}" if channel else ""}.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # delete the models from the db and send the embed
        for ta in class_tas:
            await self.repo.delete_ta(ta)
        ta_roles = [role for role in member.roles if await self.repo.is_ta_role(role)]
        await member.remove_roles(*ta_roles, reason=f'Removed by {str(inter.user)}')
        embed = discord.Embed(title='📔 Class TA Removed', color=Colors.Purple)
        embed.description = f'{member.mention} was removed as a TA in {len(class_tas)} ' \
                            f'class{"es" if len(class_tas) > 1 else ""}.'
        await inter.response.send_message(embed=embed)

    @ta_group.command(name='list', description='List the TAs & their info for a class.')
    async def ta_list(self, inter: discord.Interaction, channel: discord.TextChannel | None = None):
        text_channel = channel if channel else inter.channel
        if not (cls := await self.repo.search_class_by_channel(text_channel)):
            embed = error_embed(inter.user, f'The channel {text_channel.mention} is not a class channel.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        class_tas = await self.repo.get_tas_by_channel(text_channel)
        if not any(t.has_details is True for t in class_tas):
            embed = discord.Embed(title='📔 Class TAs', color=Colors.Purple)
            embed.description = f'There are no registered TAs for {cls.full_title}.'
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(title='📔 Class TAs', color=Colors.Purple)
        embed.description = f'Here are the details for registered TAs in {cls.class_code}.'
        for i, ta in enumerate(class_tas):
            if not ta.has_details:
                continue
            if ta.ta_display_tag or Staff.is_staff(inter.user):
                adder = f'{self.bot.guild.get_member(ta.ta_user_id).mention}\n'
            else:
                adder = ''
            embed.add_field(name=f'TA #{i + 1}', value=f'{adder}```{ta.ta_details}```')
        await inter.response.send_message(embed=embed, ephemeral=True)

    @ta_group.command(name='details', description='Edit the TA details of your class.')
    async def ta_details(self, inter: discord.Interaction, channel: discord.TextChannel, display_tag: bool = False):
        if not (cls := await self.repo.search_class_by_channel(channel)):
            embed = error_embed(inter.user, f'The channel {channel.mention} is not a class channel.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        if not (ta := await self.repo.get_ta(inter.user, channel)):
            embed = error_embed(inter.user, f'You are not a TA for {channel.mention}.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        await inter.response.send_modal(TAModal(self.bot, cls, ta, display_tag))

    def _find_role(self, name: str) -> discord.Role | None:
        name = name.lower()
        for role in self.bot.guild.roles:
            if role.name.lower() is name:
                return role
        return None


async def setup(bot: SockBot) -> None:
    await bot.add_cog(ManageClassesCog(bot))
