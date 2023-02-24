import asyncio
import json
import logging
from collections import deque

import aiosqlite
import discord.ext.commands as commands

import bot.bot_secrets as bot_secrets
from bot.consts import DiscordLimits
from bot.data.base_repository import BaseRepository

log = logging.getLogger(__name__)

MAX_MESSAGE_SIZE = 1900


class OwnerCog(commands.Cog):
    """ This is a cog for bot owner commands, things like log viewing and bot stats are shown here"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(hidden=True, invoke_without_command=True, case_insensitive=True)
    @commands.is_owner()
    async def owner(self, ctx):
        """For User by the bots owner to get errors and metrics"""
        pass

    @owner.group(invoke_without_command=True)
    @commands.is_owner()
    async def leave(self, ctx, id: int):
        server = self.bot.get_guild(id)
        await server.leave()

    @owner.group(invoke_without_command=True, aliases=['eval'])
    @commands.is_owner()
    async def eval_bot(self, ctx):
        pass

    @owner.group(invoke_without_command=True)
    @commands.is_owner()
    async def log(self, ctx):
        pass

    @log.command()
    @commands.is_owner()
    async def get(self, ctx, lines: int):
        log_name = log.parent.handlers[0].baseFilename
        with open(log_name, 'r') as f:
            logs = "".join(deque(f, lines))
            chunks = [logs[i:i + MAX_MESSAGE_SIZE] for i in range(0, len(logs), MAX_MESSAGE_SIZE)]
            for c in chunks:
                await ctx.send(f'```{c}```')

    @eval_bot.command()
    @commands.is_owner()
    async def bot(self, ctx, *, code):
        code = code.replace('```python', '')
        code = code.replace('```py', '')
        code = code.replace('`', '')
        code = code.replace('\n', '\n\t')
        t = [None]
        exec_globals = {'asyncio': asyncio, 'bot': self.bot, 'code': code, 'ctx': ctx, 'loop': asyncio.get_running_loop(), 't': t}
        code = 'async def foobar():\n\t' + code + '\nt[0] = loop.create_task(foobar())'
        exec(code, exec_globals)
        await asyncio.gather(t[0])

    @eval_bot.command(aliases=['db'])
    @commands.is_owner()
    async def database(self, ctx, *, query):
        """Runs arbitrary sql queries on the db in readonly mode and returns the results"""

        database_name = bot_secrets.BotSecrets.database_name
        db_path = f'database/{database_name}'
        connect_mode = 'ro'
        json_params = {
            'indent': 2,
            'separators': (',', ': ')
        }

        async with aiosqlite.connect(f'file:{db_path}?mode={connect_mode}', uri=True) as db:
            async with db.execute(query) as c:
                result = await BaseRepository().fetch_all_as_dict(c)

        json_res = json.dumps(result, **json_params)

        if len(json_res) > DiscordLimits.MessageLength:
            await ctx.send('Query result greater then discord message length limit')
            return

        await ctx.send(f'```{json_res}```')


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
