import logging

import discord
from discord import CategoryChannel

import bot.bot_secrets as bot_secrets
from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.messaging.events import Events
from bot.models.class_models import ClassSemester, ClassChannel
from bot.services.base_service import BaseService
from bot.sock_bot import SockBot

log = logging.getLogger(__name__)
MAX_CHANNELS_PER_CATEGORY = 50


class ClassService(BaseService):

    def __init__(self, *, bot: SockBot):
        super().__init__(bot)
        self.repo = ClassRepository()

    @BaseService.Listener(Events.on_class_create)
    async def on_class_create(self, inter: discord.Interaction, cls: ClassChannel):

        pass

    @BaseService.Listener(Events.on_semester_archive)
    async def on_semester_archive(self, inter: discord.Interaction | None, semester: ClassSemester):
        channels = await self.repo.get_semester_classes(semester)
        notif_channel = self._get_notifs_channel()
        for channel in channels:
            await self.on_class_archive(channel)
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
            await self._archive_fail(cls, 'No archival category to move to.')
            return
        if role := await self.bot.guild.get_role(cls.class_role_id):
            await role.delete(reason='Class archive')
        if not (channel := await self.bot.guild.get_channel(cls.channel_id)):
            await self._archive_fail(cls, f'Channel with ID {cls.channel_id} not found.')
            return
        await self._move_and_sort(category, channel)

        pass

    @BaseService.Listener(Events.on_class_unarchive)
    async def on_class_unarchive(self, inter: discord.Interaction, pref: str, num: int, prof: str):
        pass

    @BaseService.Listener(Events.on_guild_channel_delete)
    async def on_channel_delete(self, channel: discord.TextChannel):
        if class_channel := await self.repo.search_class_by_channel(channel):
            notif_channel = self._get_notifs_channel()
            if role := await self.bot.guild.get_role(class_channel.class_role_id):
                await role.delete(reason='Class deletion')
            await self.repo.delete_class(channel)
            embed = discord.Embed(title='Class Channel Deleted', color=Colors.Error)
            embed.description = f'Class channel #{class_channel.channel_name()} deleted.'
            if role:
                embed.description += f'\nThe role `@{class_channel.class_code()}` has been deleted for convenience.'
            embed.add_field(name='Semester', value=class_channel.semester_id)
            await notif_channel.send(embed=embed)

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

    async def _get_or_create_category(self, cls: ClassChannel) -> CategoryChannel:
        """
        Gets or creates a new category channel for a class channel.
        If a new category is created, the passed ClassChannel reference
        is updated, but the update is not pushed to the database.
        """
        category_name = cls.intended_category()
        for category in self.bot.guild.categories:
            if cls.category_id == category.id:
                return category
        new_category = await self.bot.guild.create_category(name=category_name)
        cls.category_id = new_category.id
        return new_category

    async def _get_or_create_role(self, cls: ClassChannel) -> discord.Role:
        """
        Gets or creates a new role for a class channel.
        If a new role is created, the passed ClassChannel reference
        is updated, but the update is not pushed to the database.
        """
        if not (role := self.bot.guild.get_role(cls.class_role_id)):
            new_role = await self.bot.guild.create_role(
                name=cls.class_code(),
                mentionable=True
            )
            cls.class_role_id = new_role.id
            return new_role
        return role

    async def _archive_fail(self, cls: ClassChannel, desc: str) -> None:
        notif_channel = self._get_notifs_channel()
        embed = discord.Embed(title='Class Archive Failed', color=Colors.Error, description=desc)
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
                self.on_semester_archive(None, semester),
                time=semester.end_date()
            )
            for channel in await self.repo.get_semester_classes(semester):
                if not self.bot.guild.get_channel(channel.channel_id):
                    await self.repo.delete_class(channel)
