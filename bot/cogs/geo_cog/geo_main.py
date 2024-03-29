# Vineet Saraf
# October 18th, 2023
import asyncio
import bot.bot_secrets as bot_secrets
import bot.cogs.geo_cog.streetviewrandomizer.countries as flagdict
import bot.extensions as ext
import discord
import discord.ext.commands as commands
import logging
from bot.cogs.geo_cog.geo_view import GeoView as GeoView
from bot.cogs.geo_cog.streetviewrandomizer.countries import COUNTRIES
from bot.cogs.geo_cog.streetviewrandomizer.street_view_random import StreetViewRandom
from bot.data.geo_repository import GeoRepository
from bot.sock_bot import SockBot
from discord.ui import Button, View
from timeit import default_timer as timer


log = logging.getLogger(__name__)

"""
 Streetview grabbing mechanism explained:
 -- Spray the map with points until street view is found.
 -- This process is expensive and uses many API calls. Which is why I optimized it by
 -- creating geographic regions that encompass dense street view places: dense countries and dense city cores.
 -- The four shapefiles store coordinate data that define polygons over specific geographic regions.
 -- While many geographic regions exist, only the ones at the top of street_view_random.py are used.
 -- This makes it as efficient as possible to find random street view.
 -- If more than 50 API calls are expensed in a region, it switches to a new country, and if it happens again,
 -- then it automatically switches to Singapore. Singapore is tiny and dense, and guaranteed to have street view.

 RESTRICTIONS:
 -- I have locked the Google Maps API to 10,000 calls per month, and may increase it to 15,000.
 -- We have a theoretical maximum of 28,000 api calls per month before Google starts charging $$$.
 -- If any contributor decides to add a new geographic region, you must contact me (Vineet Saraf) before
 -- making this addition. Adding the wrong area could cause the bot to waste API calls looking in a sparse area.

 WANNA ADD MORE CITIES AND TERRITORIES?
 -- Pick a very dense country (I've already got most of them sorry.)
 -- Pick the densest part of a city, it's needs to be as tight as possible.

 How to add new cities, geographic areas:
 0.) Open QGIS, with all 4 shapefiles.
 1.) Edit QGIS shapefile with new polygon.
    - Choose a 3 letter code that's not taken.
    - Set Name to name of the country
    - * Use country's actual ISO2 code for ISO2 section!
    - Add to CITY_NAME at will (add a comma in the database too)
 2.) Add new ISO3 code to the countries file, we will pretend this is a new country.
 3.) Add to COUNTRIES list in street_view_random.py
"""


class GeoGuessCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.repo = GeoRepository()

    # Main command for running the game.
    @ext.command()
    @commands.cooldown(1, 180, commands.BucketType.user)
    @ext.example("#geoguess game")
    @ext.long_help("Starts a game round.")
    @ext.short_help("Play game.")
    async def game(self, ctx) -> None:
        file_name = "StreetView.jpg"
        api_key = bot_secrets.secrets.geocode_key

        message = await ctx.send("I'm blindfolded throwing darts at the map, gimme a sec...")

        # Correct answer is the first member of the list, prior to shuffling
        # Pick a random country to look at
        random_sample: list = StreetViewRandom.generate_country_options()

        # Establish default values
        args = {
            'api_key': api_key,
            'countries': random_sample,
            'use_area': False,
            'headings': 0,
            'pitches': 0,
            'fovs': 110,
            'samples': 1,
            'radius': COUNTRIES[random_sample[0]],
            'size': '640x550',
            'output_dir': 'bot/cogs/geo_cog/temp_assets/',
            'location': ''
        }

        # Grab random street-view from the country, compute api response time
        start = timer()

        random_view_grab = StreetViewRandom(args)
        execute = await random_view_grab.run(args)
        new_selections: list = execute.new_selection

        end = timer()
        api_res_time: float = (end - start) * 1000

        # In case StreetViewRandom switches countries
        if len(new_selections) > 0:
            random_sample = execute.new_selection
        else:
            random_sample[0] = execute.iso3

        # Grab location and URL data
        args['location'] = f"{execute.latitude},{execute.longitude}"

        # Some entries have a city name attached, we retrieve that here.
        full_name = ""
        if len(str(StreetViewRandom.get_parameter(random_sample[0], "city"))) > 1 and not "nan":
            full_name = str(StreetViewRandom.get_parameter(random_sample[0], "city"))
            full_name += " "
            full_name += str(StreetViewRandom.get_parameter(random_sample[0], "country"))

        labels_and_emojis: dict[str] = {
            'labels': [],
            'emojis': []
        }

        for i in range(5):
            iso3 = random_sample[i]
            labels_and_emojis['labels'].append(StreetViewRandom.get_parameter(iso3, "country"))
            labels_and_emojis['emojis'].append(flagdict.FLAG_DICTIONARY[StreetViewRandom.get_parameter(iso3, "iso2")])

        new_geo_view = GeoView(args, labels_and_emojis, full_name)

        # Create the initial embed.
        initial_embed = await new_geo_view.create_embed(api_res_time, " ")
        file = discord.File(fp=f'bot/cogs/geo_cog/temp_assets/{file_name}', filename=file_name)
        await message.delete()
        await ctx.send(files=[file, initial_embed[1]], embed=initial_embed[0], view=new_geo_view)
        await new_geo_view.wait()

    @ext.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @ext.example("?geoguess lb")
    @ext.long_help("Displays the GeoguessrLeaderboard")
    @ext.short_help("GeoguessrLeaderboard")
    async def lb(self, ctx) -> None:
        guild = self.bot.get_guild(ctx.guild.id)
        new_embed = discord.Embed(color=0x00FF61)
        new_embed.set_author(name="Discord Geoguessr by @yeet.us",
                             icon_url="https://i.imgur.com/ZyGOyTg.png")
        lb_output = ""

        entries: int = 10 if (await self.repo.return_size()) >= 10 else (await self.repo.return_size())
        rank_btn = Button(label="What's my rank?", style=discord.ButtonStyle.primary, row=1)

        async def view_rank(interaction: discord.Interaction) -> None:
            if await self.repo.get_by_userid_scores_descending(interaction.user.id) is not None:
                size = (await self.repo.return_size())
                rank = 0

                for x in range(size):
                    if (await self.repo.get_rank())[x].get('user_id') == interaction.user.id:
                        rank = (await self.repo.get_rank())[x].get('RANK')

                score = (await self.repo.sort_and_return())[rank - 1].get('score')
                msg = f'You are ranked **#{rank}** and you have **{score} points**'
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.response.send_message("You aren't even on the board, "
                                                        "try a game out! Run ?geoguess game", ephemeral=True)

        view = View(timeout=None)
        rank_btn.callback = view_rank
        view.add_item(rank_btn)

        for i in range(entries):
            lb_output += f"**{i+1}.** " \
                        f"{guild.get_member((await self.repo.sort_and_return())[i].get('user_id'))} " \
                        f" **{(await self.repo.sort_and_return())[i].get('score')} points**\n"

        new_embed.add_field(name="Leaderboard", value=lb_output, inline=False)
        await ctx.send(embed=new_embed, view=view)
        await asyncio.sleep(2)


async def setup(bot: SockBot):
    await bot.add_cog(GeoGuessCog(bot))
