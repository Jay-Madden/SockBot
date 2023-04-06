import os
import random
import shutil

import bot.cogs.geo_cog.flagdict as flagdict
import discord
import requests
import time
import geopandas as gpd
import logging
import discord.ext.commands as commands
import bot.extensions as ext
import bot.bot_secrets as bot_secrets

from timeit import default_timer as timer
from discord.ui import Button, View
from bot.sock_bot import SockBot
from bot.cogs.geo_cog.streetviewrandomizer.StreetViewRandom import StreetViewRandom

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


class GeoGuessCOG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    responseTime = 0

    @staticmethod
    def pull_street_view(self, pic_params, pic_base, filename, quota) -> dict:
        if quota > 0:
            t0: int = time.time_ns()
            pic_response: requests.Response = requests.get(pic_base, params=pic_params)
            t1: int = time.time_ns()
            self.responseTime = (t1 - t0)/1000000

            for key, value in pic_response.headers.items():
                print(f"{key}: {value}")

            if os.path.exists(filename):
                filename = filename.format(int(time.time()))
                f = open(f'bot/cogs/geo_cog/tempAssets/{filename}', 'wb')
            else:
                f = open(f'bot/cogs/geo_cog/tempAssets/{filename}', 'wb')

            f.write(pic_response.content)
            f.close()
            # remember to close the response connection to the API
            pic_response.close()
            quota -= 1
        returnvals = {'filename': filename,
                      'quota': quota}
        return returnvals
    
    # Read from a dictionary, flagdict.py, the associate emoji for a (ISO3 -> ISO2) country
    @staticmethod
    def getcountryemoji(twoDigitCode):
        return flagdict.flagDictionary[twoDigitCode]
    
    @staticmethod
    def get_iso2(threeDigitCode):
        gdf: gpd.GeoDataFrame = gpd.read_file(
            "bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp")
        twoDigit = gdf.loc[gdf['ISO3'] == threeDigitCode, 'ISO2'].squeeze()
        return twoDigit
    
    @staticmethod
    def getcountryname(threeDigitCode):
        gdf: gpd.GeoDataFrame = gpd.read_file(
            "bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp")
        name = gdf.loc[gdf['ISO3'] == threeDigitCode, 'NAME'].squeeze()
        return name
   
    @staticmethod
    def getcityname(threeDigitCode):
        gdf: gpd.GeoDataFrame = gpd.read_file(
            "bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp")
        name = gdf.loc[gdf['ISO3'] == threeDigitCode, 'CITY_NAME'].squeeze()
        return name
    
    @staticmethod  # Create an embed in the format required
    def create_embed(ctx, filename, b3, b4, pic_params, quota, apirestime) -> dict:
        b3.disabled = False
        b4.disabled = False
        newEmbed: discord.Embed = discord.Embed(title="Geoguessr challenge time!",
                                                description="Can you guess where this is? 1 guess per user.",
                                                color=0x00FF61)
        newEmbed.set_image(url=f"attachment://{filename}")
        newEmbed.add_field(name="", value=f'Moves Left: {quota}', inline=True)

        file = discord.File('bot/cogs/geo_cog/northward.png',
                            filename='northward.png')

        newEmbed.set_author(name="Geoguesser by yeetusfeetus#9414",
                            icon_url="https://cdn.discordapp.com/attachments/782728868179607603/1087563023243300884/authorimg.png")

        newEmbed.set_footer(text=f"{round(apirestime)} ms",
                            icon_url="https://cdn.discordapp.com/attachments/782728868179607603/1087564659537756201/Logo-google-map-design-on-transparent-background-PNG.png")

        # Disable buttons when too far zoomed in or zoomed out
        if pic_params['fovs'] <= 30:
            b3.disabled = True
        else:
            b3.disabled = False
        if pic_params['fovs'] >= 150:
            b4.disabled = True
        else:
            b4.disabled = False
        # Adjust thumbnail to account for compass direction
        if pic_params['headings'] == 0:
            file: discord.File = discord.File('bot/cogs/geo_cog/northward.png', filename='northward.png')
            newEmbed.set_thumbnail(url='attachment://northward.png')
        elif pic_params['headings'] == 90:
            file: discord.File = discord.File('bot/cogs/geo_cog/eastward.png', filename='eastward.png')
            newEmbed.set_thumbnail(url='attachment://eastward.png')
        elif pic_params['headings'] == 180:
            file: discord.File = discord.File('bot/cogs/geo_cog/southward.png', filename='southward.png')
            newEmbed.set_thumbnail(url='attachment://southward.png')
        else:
            file: discord.File = discord.File('bot/cogs/geo_cog/westward.png', filename='westward.png')
            newEmbed.set_thumbnail(url='attachment://westward.png')
        return {'newEmbed': newEmbed, 'file': file}

    # Main command for running the game.
    @ext.command()
    @commands.cooldown(1, 0, commands.BucketType.user)
    @ext.example("?geoguess game")
    @ext.long_help("Starts a game round.")
    @ext.short_help("Play game.")
    async def game(self, ctx, *, member: discord.Member = None) -> None:
        quota:    int = 10
        filename: str = 'StreetView.jpg'
        pic_base: str = 'https://maps.googleapis.com/maps/api/streetview?'
        api_key:  str = bot_secrets.secrets.geocode_key

        # Pick a random country to look at
        c, r = random.choice(list(StreetViewRandom.Countries.items()))
        # c = "CBA"
        # r = 15

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

        # Number of moves used
        quota += 1

        # Grab location and URL data
        URL: str = execute['URL']
        args['location']: dict[str, str] = f"{execute['lat']},{execute['lon']}"

        # CREATE RANDOM BUTTON OPTIONS FOR SELECTING COUNTRIES #
        emoji_For_Country: str = self.getcountryemoji(self.get_iso2(execute['ISO3Digits']))
        listifiedCountry: list[str] = list(set(StreetViewRandom.Countries.keys()))

        curr: str = self.get_iso2(execute['ISO3Digits'])

        randChoice1 = random.choice(listifiedCountry)
        while self.get_iso2(randChoice1) == curr:
            randChoice1 = random.choice(listifiedCountry)
        randChoice1Emoji = self.getcountryemoji(self.get_iso2(randChoice1))

        randChoice2 = random.choice(listifiedCountry)
        while (self.get_iso2(randChoice2) == curr) \
                or (self.get_iso2(randChoice2) == self.get_iso2(randChoice1)):
            randChoice2 = random.choice(listifiedCountry)
        randChoice2Emoji = self.getcountryemoji(self.get_iso2(randChoice2))

        randChoice3 = random.choice(listifiedCountry)
        while (self.get_iso2(randChoice3) == curr) \
                or (self.get_iso2(randChoice3) == self.get_iso2(randChoice1)) \
                or (self.get_iso2(randChoice3) == self.get_iso2(randChoice2)):
            randChoice3 = random.choice(listifiedCountry)
        randChoice3Emoji = self.getcountryemoji(self.get_iso2(randChoice3))

        randChoice4 = random.choice(listifiedCountry)
        while (self.get_iso2(randChoice4) == curr) \
                or (self.get_iso2(randChoice4) == self.get_iso2(randChoice1)) \
                or (self.get_iso2(randChoice4) == self.get_iso2(randChoice2)) \
                or (self.get_iso2(randChoice4) == self.get_iso2(randChoice3)):
            randChoice4 = random.choice(listifiedCountry)
        randChoice4Emoji = self.getcountryemoji(self.get_iso2(randChoice4))

        # Create the row of image options
        b1: Button = Button(label="Turn LEFT", style=discord.ButtonStyle.secondary, emoji="👈", row=1)
        b2: Button = Button(label="Turn RIGHT", style=discord.ButtonStyle.secondary, emoji="👉", row=1)
        b3: Button = Button(label="Zoom IN", style=discord.ButtonStyle.secondary, emoji="🔍", row=1)
        b4: Button = Button(label="Zoom OUT", style=discord.ButtonStyle.secondary, emoji="🔭", row=1)

        # Create the row of country selections
        o1: Button = Button(label=self.getcountryname(execute['ISO3Digits']),
                            style=discord.ButtonStyle.primary,
                            emoji=emoji_For_Country,
                            row=2)

        o2: Button = Button(label=self.getcountryname(randChoice1),
                            style=discord.ButtonStyle.primary,
                            emoji=randChoice1Emoji,
                            row=2)

        o3: Button = Button(label=self.getcountryname(randChoice2),
                            style=discord.ButtonStyle.primary,
                            emoji=randChoice2Emoji,
                            row=2)

        o4: Button = Button(label=self.getcountryname(randChoice3),
                            style=discord.ButtonStyle.primary,
                            emoji=randChoice3Emoji,
                            row=2)

        o5: Button = Button(label=self.getcountryname(randChoice4),
                            style=discord.ButtonStyle.primary,
                            emoji=randChoice4Emoji,
                            row=2)

        # Create the embed
        N: dict = self.create_embed(ctx, filename, b3, b4, args, quota, apirestime)
        file = discord.File(fp=f'bot/cogs/geo_cog/tempAssets/{filename}', filename=filename)

        # Track the users who have selected any buttons
        users_clicked: list = []

        # Create functions to handle four image functionalities: zoom in, zoom out, turn left and turn right.
        async def pan_left(interaction) -> None:
            nonlocal quota
            args['headings'] = ((args['headings'] - 90) % 360)

            passThis = {'heading': args['headings'],
                        'pitch': args['pitches'],
                        'fov': args['fovs'],
                        'key': args['api_key'],
                        'location': args['location'],
                        'size': args['size']}
            start1: float = timer()
            container: dict = self.pull_street_view(self, passThis, pic_base, filename, quota)
            end1: float = timer()
            apirestime1: float = (end1 - start1) * 1000

            FN = container['filename']
            quota = container['quota']
            NE: dict = self.create_embed(ctx, FN, b3, b4, args, quota, apirestime1)
            file1 = discord.File(fp=f'bot/cogs/geo_cog/tempAssets/{FN}', filename=FN)

            if quota <= 0:
                b1.disabled, b2.disabled, b3.disabled, b4.disabled = True, True, True, True

            await interaction.response.edit_message(embed=NE['newEmbed'],
                                                    attachments=[file1, NE['file']],
                                                    view=view)

        async def pan_right(interaction) -> None:
            nonlocal quota
            args['headings'] = ((args['headings'] + 90) % 360)

            passThis = {'heading': args['headings'],
                        'pitch': args['pitches'],
                        'fov': args['fovs'],
                        'key': args['api_key'],
                        'location': args['location'],
                        'size': args['size']}

            start2: float = timer()
            container: dict = self.pull_street_view(self, passThis, pic_base, filename, quota)
            end2: float = timer()
            apirestime2: float = (end2 - start2) * 1000

            FN = container['filename']
            quota = container['quota']
            NE: dict = self.create_embed(ctx, FN, b3, b4, args, quota, apirestime2)
            file2 = discord.File(fp=f'bot/cogs/geo_cog/tempAssets/{FN}', filename=FN)

            if quota <= 0:
                b1.disabled, b2.disabled, b3.disabled, b4.disabled = True, True, True, True

            await interaction.response.edit_message(embed=NE['newEmbed'],
                                                    attachments=[file2, NE['file']],
                                                    view=view)

        async def zoom_in(interaction) -> None:
            nonlocal quota
            args['fovs'] = ((args['fovs'] - 40) % 360)

            passThis = {'heading': args['headings'],
                        'pitch': args['pitches'],
                        'fov': args['fovs'],
                        'key': args['api_key'],
                        'location': args['location'],
                        'size': args['size']}
            start3: float = timer()
            container: dict = self.pull_street_view(self, passThis, pic_base, filename, quota)
            end3: float = timer()
            apirestime3: float = (end3 - start3) * 1000

            FN = container['filename']
            quota = container['quota']
            NE: dict = self.create_embed(ctx, FN, b3, b4, args, quota, apirestime3)
            file3 = discord.File(fp=f'bot/cogs/geo_cog/tempAssets/{FN}', filename=FN)

            if quota <= 0:
                b1.disabled, b2.disabled, b3.disabled, b4.disabled = True, True, True, True

            await interaction.response.edit_message(embed=NE['newEmbed'],
                                                    attachments=[file3, NE['file']],
                                                    view=view)

        async def zoom_out(interaction) -> None:
            nonlocal quota
            args['fovs'] = ((args['fovs'] + 40) % 360)

            passThis = {'heading': args['headings'],
                        'pitch': args['pitches'],
                        'fov': args['fovs'],
                        'key': args['api_key'],
                        'location': args['location'],
                        'size': args['size']}
            start4: float = timer()
            container: dict = self.pull_street_view(self, passThis, pic_base, filename, quota)
            end4: float = timer()
            apirestime4: float = (end4 - start4) * 1000

            FN = container['filename']
            quota = container['quota']
            NE: dict = self.create_embed(ctx, FN, b3, b4, args, quota, apirestime4)
            file4 = discord.File(fp=f'bot/cogs/geo_cog/tempAssets/{FN}', filename=FN)

            if quota <= 0:
                b1.disabled, b2.disabled, b3.disabled, b4.disabled = True, True, True, True

            await interaction.response.edit_message(embed=NE['newEmbed'],
                                                    attachments=[file4, NE['file']],
                                                    view=view)
        # Create view to store two rows of buttons
        view = View(timeout=None)
        b1.callback = pan_left
        view.add_item(b1)

        b2.callback = pan_right
        view.add_item(b2)

        b3.callback = zoom_in
        view.add_item(b3)

        b4.callback = zoom_out
        view.add_item(b4)

        cityname: str = ""
        if self.getcityname(execute['ISO3Digits']) != "None":
            cityname = self.getcityname(execute['ISO3Digits'])
            cityname += " "

        @commands.Cog.listener()
        async def correct(interaction) -> None:
            user_id = interaction.user.id
            if user_id in users_clicked:
                return
            b1.disabled = True
            b2.disabled = True
            b3.disabled = True
            b4.disabled = True
            o1.style = discord.ButtonStyle.green
            o2.style = discord.ButtonStyle.red
            o3.style = discord.ButtonStyle.red
            o4.style = discord.ButtonStyle.red
            o5.style = discord.ButtonStyle.red
            await interaction.response.edit_message(view=view)
            msg = await interaction.original_response()
            time.sleep(5)
            await msg.edit(view=None)
            await interaction.followup.send(content=f"<@!{user_id}> got the right answer of **{ cityname }{ self.getcountryname(execute['ISO3Digits']) }**")

        async def o2incorrect(interaction) -> None:
            user_id = interaction.user.id
            if user_id in users_clicked:
                return
            users_clicked.append(user_id)
            o2.style = discord.ButtonStyle.red
            await interaction.response.edit_message(view=view)

        async def o3incorrect(interaction) -> None:
            user_id = interaction.user.id
            if user_id in users_clicked:
                return
            users_clicked.append(user_id)
            o3.style = discord.ButtonStyle.red
            await interaction.response.edit_message(view=view)

        async def o4incorrect(interaction) -> None:
            user_id = interaction.user.id
            if user_id in users_clicked:
                return
            users_clicked.append(user_id)
            o4.style = discord.ButtonStyle.red
            await interaction.response.edit_message(view=view)

        async def o5incorrect(interaction) -> None:
            user_id = interaction.user.id
            if user_id in users_clicked:
                return
            users_clicked.append(user_id)
            o5.style = discord.ButtonStyle.red
            await interaction.response.edit_message(view=view)

        o1.callback = correct
        o2.callback = o2incorrect
        o3.callback = o3incorrect
        o4.callback = o4incorrect
        o5.callback = o5incorrect

        OptionsList = list()
        OptionsList.append(o1)
        OptionsList.append(o2)
        OptionsList.append(o3)
        OptionsList.append(o4)
        OptionsList.append(o5)

        # Randomize the order of country buttons, so that option 1 isn't always right ;)
        random.shuffle(OptionsList)
        for i in OptionsList:
            view.add_item(i)

        await ctx.send(files=[file, N['file']], embed=N['newEmbed'], view=(view if quota > 0 else None))
        # Clean asset folder when done
        os.remove(f'bot/cogs/geo_cog/tempAssets/{filename}')


async def setup(bot: SockBot):
    await bot.add_cog(GeoGuessCOG(bot))
