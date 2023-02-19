import logging

import discord
from discord import CategoryChannel

import bot.bot_secrets as bot_secrets
from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.messaging.events import Events
from bot.models.class_models import ClassSemester, ClassChannel, ClassChannelScaffold
from bot.services.base_service import BaseService
from bot.sock_bot import SockBot
from bot.utils.helpers import error_embed

log = logging.getLogger(__name__)
MAX_CHANNELS_PER_CATEGORY = 50


class ClassService(BaseService):

    def __init__(self, *, bot: SockBot):
        super().__init__(bot)
        self.repo = ClassRepository()

    @BaseService.Listener(Events.on_class_create)
    async def on_class_create(self, inter: discord.Interaction, cls: ClassChannelScaffold, desc: str | None = None):
        # we should technically never enter this if statement, but just in case...
        if not (semester := await self.repo.get_current_semester()):
            embed = error_embed(inter.user, 'No current semester in session.')
            await inter.response.send_message(embed=embed)
            return
        # create and assign what we couldn't in the class modal
        category = await self._get_or_create_category(cls)
        role = await self._get_or_create_role(cls)
        channel = await self.bot.guild.create_text_channel(name=cls.channel_name(), topic=desc)
        class_channel = ClassChannel(cls.class_prefix, cls.class_number, cls.class_professor,
                                     cls.class_name, channel.id, semester.semester_id, category.id, role.id)
        # finish up by moving, sorting, and syncing permissions and push the new class to the repo
        await self._move_and_sort(category, channel)
        await self._sync_perms(class_channel)
        await self.repo.insert_class(class_channel)
        # add the class role to the given user and send the welcome message, notifs/inter embed
        await inter.user.add_roles(role, reason='Class creation')
        await self._send_welcome(class_channel, True, inter.user)
        embed = discord.Embed(title='📔 Class Channel Created', color=Colors.Purple)
        embed.description = f'Your new class channel has been created: {channel.mention}'
        embed.add_field(name='Class Title', value=cls.full_title(), inline=False)
        embed.add_field(name='Semester', value=semester.semester_name)
        embed.add_field(name='Professor', value=cls.class_professor)
        embed.add_field(name='Created by', value=inter.user.mention)
        await self._get_notifs_channel().send(embed=embed)
        await inter.response.send_message(embed=embed)

    @BaseService.Listener(Events.on_class_insert)
    async def on_class_insert(self,
                              inter: discord.Interaction,
                              cls: ClassChannelScaffold,
                              channel: discord.TextChannel,
                              desc: str | None = None):
        # we should technically never enter this if statement, but just in case...
        if not (semester := await self.repo.get_current_semester()):
            embed = error_embed(inter.user, 'No current semester in session.')
            await inter.response.send_message(embed=embed)
            return

        pass

    @BaseService.Listener(Events.on_semester_archive)
    async def on_semester_archive(self, semester: ClassSemester, inter: discord.Interaction | None = None):
        # go through each channel we have in the semester that is unarchived and archive it
        channels = await self.repo.get_semester_classes(semester)
        notif_channel = self._get_notifs_channel()
        for channel in channels:
            await self.on_class_archive(channel)
        # send out the embed now that we're finished
        embed = discord.Embed(title='📔 Semester Archived', color=Colors.Purple)
        embed.add_field(name='Semester', value=semester.semester_name)
        embed.add_field(name='Class Count', value=len(channels))
        embed.add_field(name='Archived By', value=inter.user.mention if inter else 'System')
        await notif_channel.send(embed=embed)
        if inter:
            await inter.response.send_message(embed=embed, ephemeral=True)

    @BaseService.Listener(Events.on_class_archive)
    async def on_class_archive(self, cls: ClassChannel, inter: discord.Interaction | None = None):
        if not (category := self._available_archive_category()):
            await self._send_failure(cls, 'Class Archive Failed', 'No archival category to move to.')
            return
        if role := self.bot.guild.get_role(cls.class_role_id):
            await role.delete(reason='Class archive')
        if not (channel := self.bot.guild.get_channel(cls.channel_id)):
            await self._send_failure(cls, 'Class Archive Failed', f'Channel with ID `{cls.channel_id}` not found.')
            return
        await self._move_and_sort(category, channel)
        await self.repo.set_archived(cls, True)
        embed = discord.Embed(title='📔 Class Archived', color=Colors.Purple)
        embed.add_field(name='Class', value=channel.mention)
        embed.add_field(name='Moved To', value=category.name)
        if inter:
            embed.add_field(name='Requested By', value=inter.user.mention)
            await inter.response.send_message(embed=embed)
        await self._get_notifs_channel().send(embed=embed)

    @BaseService.Listener(Events.on_class_unarchive)
    async def on_class_unarchive(self, inter: discord.Interaction, pref: str, num: int, prof: str):
        pass

    @BaseService.Listener(Events.on_guild_channel_delete)
    async def on_channel_delete(self, channel: discord.TextChannel):
        if class_channel := await self.repo.search_class_by_channel(channel):
            notif_channel = self._get_notifs_channel()
            if role := self.bot.guild.get_role(class_channel.class_role_id):
                await role.delete(reason='Class deletion')
            await self.repo.delete_class(class_channel)
            embed = discord.Embed(title='📔 Class Channel Deleted', color=Colors.Error)
            embed.description = f'Class channel #{class_channel.channel_name()} deleted.'
            if role:
                embed.description += f'\nThe role `@{class_channel.class_code()}` has been deleted for convenience.'
            embed.add_field(name='Semester', value=class_channel.semester_id)
            await notif_channel.send(embed=embed)

    @BaseService.Listener(Events.on_guild_role_delete)
    async def on_role_delete(self, role: discord.Role):
        if class_channel := await self.repo.search_class_by_role(role):
            class_channel.class_role_id = None
            await self.repo.update_class(class_channel)

    async def _move_and_sort(self, category: CategoryChannel, channel: discord.TextChannel):
        """
        Moves the given discord.TextChannel to the given discord.CategoryChannel.
        Sorts the channel based on descending order and syncs the permissions of the channel based off the category.
        """
        i = 0
        for ch in category.channels:
            if channel.name > ch.name:
                i += 1
        await channel.move(beginning=True, offset=i, category=category, sync_permissions=True)

    def _available_archive_category(self) -> CategoryChannel | None:
        """
        Gets an archive category that has room for at least one channel.
        If None is returned, there are no archive categories that are not full.
        """
        archive_categories = bot_secrets.secrets.class_archive_category_ids
        for category in self.bot.guild.categories:
            if category.id not in archive_categories:
                continue
            if len(category.channels) < MAX_CHANNELS_PER_CATEGORY:
                return category
        return None

    async def _get_or_create_category(self, cls: ClassChannelScaffold) -> CategoryChannel:
        """
        Gets or creates a new category channel for a class channel.
        If a new category is created, the passed ClassChannel reference
        is updated, but the update is not pushed to the database.
        """
        category_name = cls.intended_category()
        for category in self.bot.guild.categories:
            if category_name == category.id:
                return category
        new_category = await self.bot.guild.create_category(name=category_name)
        cls.category_id = new_category.id
        return new_category

    async def _get_or_create_role(self, cls: ClassChannelScaffold) -> discord.Role:
        """
        Gets or creates a new role for a class channel.
        If a new role is created, the passed ClassChannel reference
        is updated, but the update is not pushed to the database.
        """
        for r in self.bot.guild.roles:
            if r.name == cls.class_code():
                return r
        return await self.bot.guild.create_role(
            name=cls.class_code(),
            mentionable=True
        )

    async def _sync_perms(self, cls: ClassChannel) -> None:
        role = await self._get_or_create_role(cls)
        cleanup = await self._get_or_create_cleanup()
        if not (channel := self.bot.guild.get_channel(cls.channel_id)):
            await self._send_failure(cls, 'Syncing Perms Failed', f'The channel `{cls.channel_id}` does not exist.')
            return
        await channel.set_permissions(role, view_channel=True)
        await channel.set_permissions(cleanup, view_channel=False)
        await role.edit(position=3)
        await cleanup.edit(position=2)

    async def _get_or_create_cleanup(self) -> discord.Role:
        for role in self.bot.guild.roles:
            if role.name == 'Cleanup':
                return role
        return await self.bot.guild.create_role(name='Cleanup')

    async def _send_welcome(self, cls: ClassChannel, just_created: bool, user: discord.User) -> None:
        if not (semester := await self.repo.get_current_semester()):
            await self._send_failure(cls, 'Welcome Message Failed', 'There is no current semester in session.')
            return
        if not (channel := self.bot.guild.get_channel(cls.channel_id)):
            await self._send_failure(cls, 'Welcome Message Failed', f'The channel `{cls.channel_id}` does not exist.')
            return
        embed = discord.Embed(title=f'📔 {cls.full_title()}', color=Colors.Purple)
        embed.description = f'Welcome back, students!\nClick the ✅ reaction below to join the class.'
        embed.add_field(name='Semester', value=semester.semester_name)
        embed.add_field(name='Professor', value=cls.class_professor)
        embed.add_field(name='Created by' if just_created else 'Unarchived by', value=user.mention, inline=False)
        message = await channel.send(embed=embed)
        await message.add_reaction('✅')
        # TODO: Reaction service

    async def _send_failure(self, cls: ClassChannel, title: str, desc: str) -> None:
        notif_channel = self._get_notifs_channel()
        embed = discord.Embed(title=f'📔 {title}', color=Colors.Error, description=f'{desc}\nHere are some details.')
        embed.add_field(name='Semester', value=cls.semester_id)
        embed.add_field(name='Channel Name', value=cls.channel_name())
        embed.add_field(name='Archived', value=cls.class_archived)
        embed.add_field(name='Channel ID', value=cls.channel_id)
        embed.add_field(name='Role ID', value=cls.class_role_id)
        embed.add_field(name='Category ID', value=cls.category_id)
        await notif_channel.send(embed=embed)

    def _get_notifs_channel(self) -> discord.TextChannel:
        channel = self.bot.guild.get_channel(bot_secrets.secrets.class_notifs_channel_id)
        assert channel is not None
        return channel

    async def load_service(self):
        if semester := await self.repo.get_current_semester():
            self.bot.scheduler.schedule_at(
                self.on_semester_archive(semester),
                time=semester.end_date()
            )
            for channel in await self.repo.get_semester_classes(semester):
                if not self.bot.guild.get_channel(channel.channel_id):
                    await self.repo.delete_class(channel)
