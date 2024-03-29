import json
import logging
import random
import time

import aiohttp
import discord
import discord.ext.commands as commands

import bot.extensions as ext
from bot.consts import Colors
from bot.messaging.events import Events

log = logging.getLogger(__name__)


class RandomCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @ext.command()
    @ext.long_help(
        'Simply flips a coin in discord'
    )
    @ext.short_help('Flip a coin!')
    @ext.example('flip')
    async def flip(self, ctx):

        random.seed(time.time())

        embed = discord.Embed(title='Coin Flip', color=Colors.Purple)

        heads = discord.File(filename='Heads.jpg',
                             fp='bot/cogs/random_cog/assets/Heads.jpg')

        tails = discord.File(filename='Tails.jpg',
                             fp='bot/cogs/random_cog/assets/Tails.jpg')

        if random.randint(0, 1) == 1:
            attachment = heads
            embed.set_thumbnail(url='attachment://Heads.jpg')
        else:
            attachment = tails
            embed.set_thumbnail(url='attachment://Tails.jpg')

        await ctx.send(embed=embed, file=attachment)

    @ext.command(aliases=['roll', 'dice'])
    @ext.long_help(
        """
        Rolls dice in a XdY format where X is the number of dice and Y is the number of sides on the dice.
            Example:
            1d6     -   Rolls 1 die with 6 sides
            2d8     -   Rolls 2 die with 8 sides
            3d10    -   Rolls 3 die with 10 sides
            4d20    -   Rolls 4 die with 20 sides
        """
    )
    @ext.short_help('Rolls any type of dice in discord')
    @ext.example(('roll 1d6', 'roll 4d20'))
    async def diceroll(self, ctx, dice: str):
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await ctx.send('Entry has to be in a XdY format! See the help command for an example.')
            return

        result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))

        embed = discord.Embed(title='Dice Roller', description=f'{ctx.message.author.mention} rolled **{dice}**', color=Colors.Purple)
        embed.add_field(name='Here are the results of their rolls: ', value=result, inline=False)
        await ctx.send(embed=embed)

    @ext.command(aliases=['8ball', '🎱'])
    @ext.long_help(
        'Rolls a magic 8ball to tell you your future, guarenteed to work!'
    )
    @ext.short_help('Know your future')
    @ext.example(('ball Will I have a good day today?', '8ball Will I have a bad day today?'))
    async def ball(self, ctx, *, question):
        responses = [
            'It is certain.',
            'It is decidedly so.',
            'Without a doubt.',
            'Yes – definitely.',
            'You may rely on it.',
            'As I see it, yes.',
            'Most likely.',
            'Outlook good.',
            'Yes.',
            'Signs point to yes.',
            'Reply hazy, try again.',
            'Ask again later.',
            'Better not tell you now.',
            'Cannot predict now.',
            'Concentrate and ask again.',
            'Don\'t count on it.',
            'My reply is no.',
            'My sources say no.',
            'Outlook not so good.',
            'Very doubtful.'
        ]
        embed = discord.Embed(title='🎱', description=f'{random.choice(responses)}', color=Colors.Purple)
        await ctx.send(embed=embed)

    @ext.command(aliases=['relevant'])
    @ext.long_help(
        'Theres always a relevant xkcd for any situation, see if you get lucky with a random one!'
    )
    @ext.short_help('"relevant xkcd"')
    @ext.example('xkcd')
    async def xkcd(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with await session.get(url='https://c.xkcd.com/random/comic/') as resp:
                if (resp.status == 200):
                    msg = await ctx.send(resp.url)
                    await self.bot.messenger.publish(Events.on_set_deletable, msg=msg, author=ctx.author, timeout=60)
                else:
                    response_info = json.loads(await resp.text())['meta']
                    embed = discord.Embed(title='xkcd', color=Colors.Error)
                    embed.add_field(name='Error', value=f"{response_info['status']}: {response_info['msg']}")
                    msg = await ctx.send(embed=embed)
                    await self.bot.messenger.publish(Events.on_set_deletable, msg=msg, author=ctx.author, timeout=60)


async def setup(bot):
    await bot.add_cog(RandomCog(bot))
