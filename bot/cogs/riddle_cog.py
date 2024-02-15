import logging
import random

import aiohttp
import discord
import discord.ext.commands as commands

import bot.extensions as ext
import bot.bot_secrets as bot_secrets
from bot.consts import Colors

log = logging.getLogger(__name__)
RIDDLES_API_URL = 'https://api.api-ninjas.com/v1/riddles'

EMOJI_MAP = {
    '🇦': 0,
    '🇧': 1,
    '🇨': 2,
    '🇩': 3
}
REV_EMOJI_MAP = {
    0: '🇦',
    1: '🇧',
    2: '🇨',
    3: '🇩'
}

class RiddleCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    
    ##########################
    # USER EXECUTABLE COMMANDS    
    # Guess the riddle
    @ext.group(case_insensitive=True, invoke_without_command=True, aliases=['riddler'])
    @ext.long_help(
        """
        This command allows you to play a riddle guessing game.

        Choose between 4 answers to guess the riddle's answer.
        """
    )
    @ext.short_help('Guess a riddle!')
    @ext.example(('riddle', 'riddler'))
    async def riddle(self, ctx):
        self.api_ninjas_key = bot_secrets.secrets.api_ninjas_key

        headers = {
            'X-Api-Key': self.api_ninjas_key
        }

        params = {
            'limit': 4
        }
        
        try:
            async with aiohttp.request("GET", RIDDLES_API_URL, headers=headers, params=params) as response:
                if (response.status != 200):
                    embed = discord.Embed(title='The Riddler (in Socks)', color=Colors.Error)
                    ErrMsg = f'Error Code: {response.status}'
                    embed.add_field(name='Error with the riddle API', value=ErrMsg, inline=False)
                    await ctx.send(embed=embed)
                    return
                riddle_list = await response.json()
        except Exception as err:
            raise Exception(err).with_traceback(err.__traceback__)
        
        correct_riddle = riddle_list[0]

        # Keep track of original index since 0 is correct
        answers = [
            {
                "answer": riddle.get("answer", "default answer"),
                "index": index
            } 
            for index, riddle in enumerate(riddle_list)
            ]
        random.shuffle(answers)

        options_text = ""
        for index, answer in enumerate(answers):
            options_text += f"{REV_EMOJI_MAP[index]} : {answer.get('answer', '')}\n\n"

        embed = discord.Embed(title='The Riddler (in Socks)', color=Colors.Purple)
        embed.add_field(name=correct_riddle.get("title", "Riddle:"), value=correct_riddle.get("question", "No question. :\'("), inline=False)
        embed.add_field(name="Options:", value=options_text, inline=False)
        message = await ctx.send(embed=embed)

        for key in EMOJI_MAP.keys():
            await message.add_reaction(key)

        reaction, _ = await self.bot.wait_for(
            "reaction_add",
            check=lambda r, u: r.message.id == message.id
            and ctx.author.id == u.id,
            timeout=None,
        )

        await message.delete()

        # This means it is correct
        if answers[EMOJI_MAP[reaction.emoji]].get("index") == 0:
            embed = discord.Embed(title='Correct!', color=0x008000)
            embed.add_field(name=correct_riddle.get("title", "Riddle:"), value=correct_riddle.get("question", "No question. :\'("), inline=False)
            embed.add_field(name="Correct Answer:", value=correct_riddle.get("answer", "default answer"), inline=False)
            embed.add_field(name="Your Answer:", value=answers[EMOJI_MAP[reaction.emoji]].get("answer", "default answer"), inline=False)
            await ctx.send(embed=embed)
        # Incorrect
        else:
            embed = discord.Embed(title='Wrong!', color=Colors.Error)
            embed.add_field(name=correct_riddle.get("title", "Riddle:"), value=correct_riddle.get("question", "No question. :\'("), inline=False)
            embed.add_field(name="Correct Answer:", value=correct_riddle.get("answer", "default answer"), inline=False)
            embed.add_field(name="Your Answer:", value=answers[EMOJI_MAP[reaction.emoji]].get("answer", "default answer"), inline=False)
            await ctx.send(embed=embed)

        return

async def setup(bot):
    await bot.add_cog(RiddleCog(bot))