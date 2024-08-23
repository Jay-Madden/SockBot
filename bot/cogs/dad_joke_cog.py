import logging
import random

import aiohttp
import discord
import discord.ext.commands as commands

import bot.extensions as ext
from bot.consts import Colors

log = logging.getLogger(__name__)
DAD_JOKE_URL = 'https://icanhazdadjoke.com/'

REQ_HEADERS = {
    'User-Agent': 'SockBot (https://github.com/Jay-Madden/SockBot)',
    'Accept' : 'application/json'
}

class DadJokeCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    ##########################
    # USER EXECUTABLE COMMANDS    
    # Random Dad Joke
    @ext.group(case_insensitive=True, invoke_without_command=True, aliases=['dad', 'dj'])
    @ext.long_help(
        """
        This command provides a random dad joke.
        """
    )
    @ext.short_help('Get a Dad Joke!')
    @ext.example(('dadjoke', 'dad', 'dj'))
    async def dadjoke(self, ctx):
        try:
            async with aiohttp.request("GET", DAD_JOKE_URL, headers=REQ_HEADERS) as response:
                if (response.status != 200):
                    embed = discord.Embed(title='SockDad', color=Colors.Error)
                    ErrMsg = f'Error Code: {response.status}'
                    embed.add_field(name='Error with the dad joke API', value=ErrMsg, inline=False)
                    await ctx.send(embed=embed)
                    return
                joke_json = await response.json()
        except Exception as err:
            raise Exception(err).with_traceback(err.__traceback__)
        
        embed = discord.Embed(title='SockDad', color=Colors.Purple)
        embed.add_field(name='Joke:', value=joke_json.get("joke", ""), inline=False)
        await ctx.send(embed=embed)
        return
    
    # Dad joke with a focus term.
    @dadjoke.command()
    @ext.long_help(
        """
        This command provides a dad joke for a given term.
        
        Sometimes a Dad needs some direction.
        """
    )
    @ext.short_help('Get a special Dad Joke!')
    @ext.example(('dadjoke focus <term>', 'dad focus hipster', 'dj focus dog'))
    async def focus(self, ctx, term):

        req_params = {
            'term': term,
            'limit': 30
        }

        try:
            async with aiohttp.request("GET", DAD_JOKE_URL + 'search', headers=REQ_HEADERS, params=req_params) as response:
                if (response.status != 200):
                    embed = discord.Embed(title='SockDad', color=Colors.Error)
                    ErrMsg = f'Error Code: {response.status}'
                    embed.add_field(name='Error with the dad joke API', value=ErrMsg, inline=False)
                    await ctx.send(embed=embed)
                    return
                joke_json = await response.json()
        except Exception as err:
            raise Exception(err).with_traceback(err.__traceback__)
        
        joke = joke_json.get("results", [])

        if len(joke) > 0:
            joke = random.choice(joke).get("joke", "")
        else:
            joke = 'No results for that term. :\'('

        embed = discord.Embed(title='SockDad', color=Colors.Purple)
        embed.add_field(name='Joke:', value=joke, inline=False)
        await ctx.send(embed=embed)
        return


async def setup(bot):
    await bot.add_cog(DadJokeCog(bot))