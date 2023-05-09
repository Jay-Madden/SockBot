# Vineet Saraf
# May 9th, 2023

import os
import random
import aiohttp as aiohttp
import asyncio
import math
import bot.cogs.geo_cog.streetviewrandomizer.countries as flagdict
import discord
import time
import geopandas as gpd
import logging
import discord.ext.commands as commands
import bot.extensions as ext
import bot.bot_secrets as bot_secrets
import bot as bot
from bot.cogs.geo_cog.geo_view import geo_view as geo_view

from timeit import default_timer as timer
from discord.ui import Button, View
from bot.sock_bot import SockBot
from bot.cogs.geo_cog.streetviewrandomizer.StreetViewRandom import StreetViewRandom
from bot.data.geo_repository import GeoGuessrRepository
from bot.cogs.geo_cog.streetviewrandomizer.countries import Countries


log = logging.getLogger(__name__)


# Streetview grabbing mechanism explained:
# -- Spray the map with points until street view is found.
# -- This process is expensive and uses many API calls. Which is why I optimized it by
# -- creating geographic regions that encompass dense street view places: dense countries and dense city cores.
# -- The four shapefiles store coordinate data that define polygons over specific geographic regions.
# -- While many geographic regions exist, only the ones at the top of StreetViewRandom.py are used.
# -- This makes it as efficient as possible to find random street view.
# -- If more than 50 API calls are expensed in a region, it switches to a new country, and if it happens again,
# -- then it automatically switches to Singapore. Singapore is tiny and dense, and guaranteed to have street view.
#
# RESTRICTIONS:
# -- I have locked the Google Maps API to 10,000 calls per month, and may increase it to 15,000.
# -- We have a theoretical maximum of 28,000 api calls per month before Google starts charging $$$.
# -- If any contributor decides to add a new geographic region, you must contact me (Vineet Saraf) before
# -- making this addition. Adding the wrong area could cause the bot to waste API calls looking in a sparse area.
#
# WANNA ADD MORE CITIES AND TERRITORIES?
# -- Pick a very dense country (I've already got most of them sorry.)
# -- Pick the densest part of a city, it's needs to be as tight as possible.
#
# How to add new cities, geographic areas:
# 0.) Open QGIS, with all 4 shapefiles.
# 1.) Edit QGIS shapefile with new polygon.
#    - Choose a 3 letter code that's not taken.
#    - Set Name to name of the country
#    - * Use country's actual ISO2 code for ISO2 section!
#    - Add to CITY_NAME at will (add a comma in the database too)
# 2.) Add new ISO3 code to the countries file, we will pretend this is a new country.
# 3.) Add to Countries list in StreetViewRandom.py

filename: str = 'StreetView.jpg'
pic_base: str = 'https://maps.googleapis.com/maps/api/streetview?'
api_key:  str = bot_secrets.secrets.geocode_key
quota_per_game = 10
pan_and_zoom: list


class GeoGuessCOG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.repo = GeoGuessrRepository()

    @staticmethod
    async def update_user_score(user_id, final_Score):
        if await GeoGuessrRepository.get_best_preparation_for_member(user_id) is None:
            await GeoGuessrRepository.add_into(user_id, final_Score)
        else:
            existingScore = (await GeoGuessrRepository.get_existing_score(user_id)) + final_Score
            await GeoGuessrRepository.repo.update_score(existingScore, user_id)

    @staticmethod
    def pull_street_view(pic_params: dict, pic_base: str, filename: str) -> tuple:
        global quota_per_game
        if quota_per_game > 0:
            async def get_thing():
                async with aiohttp.ClientSession().get(url=pic_base, params=pic_params, allow_redirects=False) as resp:
                    return await resp.read()
            pic_response = asyncio.get_event_loop().run_until_complete(get_thing())

            if os.path.exists(filename):
                filename = filename.format(int(time.time()))
                f = open(f'bot/cogs/geo_cog/tempAssets/{filename}', 'wb')
            else:
                f = open(f'bot/cogs/geo_cog/tempAssets/{filename}', 'wb')

            f.write(pic_response)
            f.close()
            quota_per_game -= 1
        returnvals = (filename, quota_per_game)
        return returnvals
    
    # Read from a dictionary, flagdict.py, the associate emoji for a (ISO3 -> ISO2) country
    @staticmethod
    def getcountryemoji(twoDigitCode):
        return flagdict.flagDictionary[twoDigitCode]

    @staticmethod
    def get_parameter(threeDigitCode: str, iso2: bool, country: bool, city: bool):
        gdf: gpd.GeoDataFrame = gpd.read_file(
            "bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp")
        if iso2:
            return gdf.loc[gdf['ISO3'] == threeDigitCode, 'ISO2'].squeeze()
        elif country:
            return gdf.loc[gdf['ISO3'] == threeDigitCode, 'NAME'].squeeze()
        elif city:
            return gdf.loc[gdf['ISO3'] == threeDigitCode, 'CITY_NAME'].squeeze()

    @staticmethod  # Create an embed in the format required
    def create_embed(filename, b3, b4, pic_params, quota, apirestime) -> tuple:
        b3.disabled = False
        b4.disabled = False
        newEmbed: discord.Embed = discord.Embed(title="Geoguessr challenge time!",
                                                description="Can you guess where this is? 1 guess per user.",
                                                color=0x00FF61)
        newEmbed.set_image(url=f"attachment://{filename}")
        newEmbed.add_field(name="", value=f'Moves Left: {quota}', inline=True)

        newEmbed.set_author(name="Geoguessr by yeetusfeetus#9414",
                            icon_url="https://i.imgur.com/ZyGOyTg.png")

        newEmbed.set_footer(text=f"{round(apirestime)} ms. Use \"?geoguess lb\" for the GeoguessrLeaderboard.",
                            icon_url="https://i.imgur.com/Y4gnqiV.png")

        # Disable buttons when too far zoomed in or zoomed out
        b3.disabled = pic_params['fovs'] <= 30
        b4.disabled = pic_params['fovs'] >= 150

        # Adjust thumbnail to account for compass direction
        file_name: str
        match pic_params['headings']:
            case 0:
                file_name = 'northward.png'
            case 90:
                file_name = 'eastward.png'
            case 180:
                file_name = 'southward.png'
            case _:
                file_name = 'westward.png'
        file = discord.File(f'bot/cogs/geo_cog/Assets/{file_name}', filename=file_name)
        newEmbed.set_thumbnail(url=f'attachment://{file_name}')

        return newEmbed, file

    @staticmethod
    def decay_score(start_score: int, start: int, end: int):
        return int(start_score * math.exp((-1 / 28) * (end - start)))

    # Main command for running the game.
    @ext.command()
    @commands.cooldown(1, 180, commands.BucketType.user)
    @ext.example("?geoguess game")
    @ext.long_help("Starts a game round.")
    @ext.short_help("Play game.")
    async def game(self, ctx) -> None:
        global filename, pic_base, api_key, quota_per_game, pan_and_zoom
        await ctx.send("I'm blindfolded throwing darts at the map, gimme a sec...", delete_after=5)

        # Pick a random country to look at
        c, r = random.choice(list(Countries.items()))

        # Establish default values
        args = {
            'api_key': api_key,
            'countries': c,
            'use_area': False,
            'headings': 0,
            'pitches': 0,
            'fovs': 110,
            'samples': 1,
            'radius': r,
            'size': '640x550',
            'output_dir': 'bot/cogs/geo_cog/tempAssets/',
            'location': None
        }

        # Grab random street-view from the country, compute api response time
        start: float = timer()
        randomViewGrab: StreetViewRandom = StreetViewRandom(args)
        execute: dict[str, str] = randomViewGrab.run(args)
        end: float = timer()
        apirestime: float = (end - start) * 1000

        # Grab location and URL data
        args['location']: dict[str, str] = f"{execute[1]},{execute[2]}"

        # CREATE RANDOM BUTTON OPTIONS FOR SELECTING COUNTRIES #

        # Correct Answer
        emoji_For_Country: str = self.getcountryemoji(self.get_parameter(execute[3], True, False, False))

        # Wrong Answers
        listifiedCountry: list[str] = list(Countries.keys())
        randchoices = random.sample(listifiedCountry, 4)

        # Duplication prevention protocol
        for i in range(4):
            while self.getcountryemoji(self.get_parameter(randchoices[i], True, False, False)) == emoji_For_Country:
                randchoices = random.sample(listifiedCountry, 4)

        # Set the random choices
        randChoice1 = randchoices[0]
        randChoice1Emoji = self.getcountryemoji(self.get_parameter(randChoice1, True, False, False))

        randChoice2 = randchoices[1]
        randChoice2Emoji = self.getcountryemoji(self.get_parameter(randChoice2, True, False, False))

        randChoice3 = randchoices[2]
        randChoice3Emoji = self.getcountryemoji(self.get_parameter(randChoice3, True, False, False))

        randChoice4 = randchoices[3]
        randChoice4Emoji = self.getcountryemoji(self.get_parameter(randChoice4, True, False, False))

        # Create the row of image options
        b1 = Button(label="Turn LEFT", style=discord.ButtonStyle.secondary, emoji="👈", row=1)
        b2 = Button(label="Turn RIGHT", style=discord.ButtonStyle.secondary, emoji="👉", row=1)
        b3 = Button(label="Zoom IN", style=discord.ButtonStyle.secondary, emoji="🔍", row=1)
        b4 = Button(label="Zoom OUT", style=discord.ButtonStyle.secondary, emoji="🔭", row=1)
        pan_and_zoom = [b1, b2, b3, b4]

        # Create the row of country selections
        o1 = Button(label=self.get_parameter(execute[3], False, True, False),
                    style=discord.ButtonStyle.primary,
                    emoji=emoji_For_Country,
                    row=2)

        o2 = Button(label=self.get_parameter(randChoice1, False, True, False),
                    style=discord.ButtonStyle.primary,
                    emoji=randChoice1Emoji,
                    row=2)

        o3 = Button(label=self.get_parameter(randChoice2, False, True, False),
                    style=discord.ButtonStyle.primary,
                    emoji=randChoice2Emoji,
                    row=2)

        o4 = Button(label=self.get_parameter(randChoice3, False, True, False),
                    style=discord.ButtonStyle.primary,
                    emoji=randChoice3Emoji,
                    row=2)

        o5 = Button(label=self.get_parameter(randChoice4, False, True, False),
                    style=discord.ButtonStyle.primary,
                    emoji=randChoice4Emoji,
                    row=2)

        # Create the embed
        N = self.create_embed(filename, b3, b4, args, quota_per_game, apirestime)
        file = discord.File(fp=f'bot/cogs/geo_cog/tempAssets/{filename}', filename=filename)

        # Track the users who have selected any buttons
        users_clicked: list = []

        # Create view to store two rows of buttons
        view = View(timeout=None)

        # Enable panning and zooming functionality for the 4 utility buttons
        async def pan_left(interaction: discord.Interaction):
            await geo_view.navigate(interaction, view, args, pan_and_zoom, users_clicked,
                                    interaction.user.id, True, False, False, False)
        b1.callback = pan_left
        view.add_item(b1)

        async def pan_right(interaction: discord.Interaction):
            await geo_view.navigate(interaction, view, args, pan_and_zoom, users_clicked,
                                    interaction.user.id, False, True, False, False)
        b2.callback = pan_right
        view.add_item(b2)

        async def zoom_in(interaction: discord.Interaction):
            await geo_view.navigate(interaction, view, args, pan_and_zoom, users_clicked,
                                    interaction.user.id, False, False, True, False)
        b3.callback = zoom_in
        view.add_item(b3)

        async def zoom_out(interaction: discord.Interaction):
            await geo_view.navigate(interaction, view, args, pan_and_zoom, users_clicked,
                                    interaction.user.id, False, False, False, True)
        b4.callback = zoom_out
        view.add_item(b4)

        OptionsList = [o1, o2, o3, o4, o5]

        # Some entries have a city name attachted, we retrieve that here.
        cityname: str = ""
        if self.get_parameter(execute[3], False, False, True) != "None":
            cityname = self.get_parameter(execute[3], False, False, True)
            cityname += " "

        # Assign the callback functions for which buttons are correct and which are incorrect 
        async def o1callback(interaction: discord.Interaction) -> None:
            nonlocal users_clicked, OptionsList
            country: str = self.get_parameter(execute[3], False, True, False)
            await geo_view.correct(interaction, initial_score, scoreDecay, users_clicked,
                                   pan_and_zoom, OptionsList, view, country, cityname, interaction.user.id, o1)
        o1.callback = o1callback

        async def o2callback(interaction: discord.Interaction) -> None:
            nonlocal users_clicked
            await geo_view.incorrect(o2, view, users_clicked, interaction.user.id, interaction)
        o2.callback = o2callback

        async def o3callback(interaction: discord.Interaction) -> None:
            nonlocal users_clicked
            await geo_view.incorrect(o3, view, users_clicked, interaction.user.id, interaction)
        o3.callback = o3callback

        async def o4callback(interaction: discord.Interaction) -> None:
            nonlocal users_clicked
            await geo_view.incorrect(o4, view, users_clicked, interaction.user.id, interaction)
        o4.callback = o4callback

        async def o5callback(interaction: discord.Interaction) -> None:
            nonlocal users_clicked
            await geo_view.incorrect(o5, view, users_clicked, interaction.user.id, interaction)
        o5.callback = o5callback

        # Randomize the order of country buttons, so that option 1 isn't always right ;)
        random.shuffle(OptionsList)
        for i in range(5):
            view.add_item(OptionsList[i])

        await ctx.send(files=[file, N[1]], embed=N[0], view=(view if quota_per_game > 0 else None))
        initial_score: int = 5000
        scoreDecay: float = timer()

    @ext.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @ext.example("?geoguess lb")
    @ext.long_help("Displays the GeoguessrLeaderboard")
    @ext.short_help("GeoguessrLeaderboard")
    async def lb(self, ctx) -> None:
        newEmbed: discord.Embed = discord.Embed(color=0x00FF61)
        newEmbed.set_author(name="Discord Geoguessr by yeetusfeetus#9414",
                            icon_url="https://i.imgur.com/ZyGOyTg.png")
        LBoutput: str = ""

        entries: int = 10 if (await self.repo.return_size()) >= 10 else (await self.repo.return_size())
        RankBTN: Button = Button(label="What's my rank?", style=discord.ButtonStyle.primary, row=1)

        async def view_rank(interaction) -> None:
            if await self.repo.get_best_preparation_for_member(interaction.user.id) is not None:
                Size: int = (await self.repo.return_size())
                Rank: int = 0

                for X in range(Size):
                    if (await self.repo.get_rank())[X].get('user_id') == interaction.user.id:
                        Rank = (await self.repo.get_rank())[X].get('RANK')

                Score: int = (await self.repo.sort_and_return())[Rank - 1].get('score')
                MSG: str = f'You are ranked **#{Rank}** and you have **{Score} points**'
                await interaction.response.send_message(MSG, ephemeral=True)
            else:
                await interaction.response.send_message(f'You aren\'t even on the board, '
                                                        f'try a game out! Run ?geoguess game', ephemeral=True)

        view = View(timeout=None)
        RankBTN.callback = view_rank
        view.add_item(RankBTN)

        for i in range(entries):
            LBoutput += f"**{i+1}.** " \
                        f"{ctx.guild.get_member((await self.repo.sort_and_return())[i].get('user_id'))} -" \
                        f" **{(await self.repo.sort_and_return())[i].get('score')} points**\n"

        newEmbed.add_field(name="Leaderboard", value=LBoutput, inline=False)
        await ctx.send(embed=newEmbed, view=view)
        time.sleep(2)


async def setup(bot: SockBot):
    await bot.add_cog(GeoGuessCOG(bot))
