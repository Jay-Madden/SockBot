import logging
from math import radians, cos, sin, asin, sqrt, atan2, pi
import re

import aiohttp
import discord
import discord.ext.commands as commands

import bot.extensions as ext
import bot.bot_secrets as bot_secrets
from bot.consts import Colors
from bot.messaging.events import Events

log = logging.getLogger(__name__)
URL_GEO = "https://geocode.xyz/"

class DistanceCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Function to get coordinates from the API if not presented by the user
    async def getCoords(self, ctx, loc, loc_number):
        # Remove any characters not in ranges a-z, A-Z, or 0-9
        # Exceptions: & _ - , . and <space>
        # per the ASCII Table https://www.asciitable.com
        loc = re.sub("[^a-zA-Z0-9.,&_-]+", "", loc)

        # if a user enters coords, dont query the API
        if re.search("^\d{1,3}\.\d+,\d{1,3}\.\d+", loc):
            return loc.split(",")[0], loc.split(",")[1], f'({loc})'

        # Geocoding URL
        url_Geo_API = f'{URL_GEO}{loc}'

        self.geocode_api_key = bot_secrets.secrets.geocode_key

        geo_queryparams = {
            'auth': self.geocode_api_key,
            'json': '1',
        }

        # Message to Display while APIs are called
        wait_msg = await ctx.send(f'Converting location {loc_number}')

        # Try Except for catching errors that could give away either API key
        try:
            async with aiohttp.request("GET", url_Geo_API, params=geo_queryparams) as response:
                if (response.status != 200):
                    embed = discord.Embed(title='Distance Calculator', color=Colors.Error)
                    ErrMsg = f'Error Code: {response.status}'
                    embed.add_field(name='Error with geocode API', value=ErrMsg, inline=False)
                    await ctx.send(embed=embed)
                    return
                res_geo_json = await response.json()
        except Exception as err:
            err_str = str(err)
            err_str = re.sub(self.geocode_api_key, "CLASSIFIED", err_str)
            raise Exception(err_str).with_traceback(err.__traceback__)

        # checks for the field standard. if this doesn't exist, then the user provided coordinates and the response is different
        city = res_geo_json.get('standard', res_geo_json).get('city', '')

        lon = res_geo_json.get('longt', None)
        lat = res_geo_json.get('latt', None)

        await wait_msg.delete()
        return lat, lon, city
    
    # Calculate the distance between two coordinates using the Haversine Formula
    # and get initial bearing of that distance
    def calculateDistance(self, lat1, lon1, lat2, lon2, is_metric):
        # convert decimal degrees to radians 
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # haversine formula 
        lon_diff = lon2 - lon1 
        lat_diff = lat2 - lat1 
        a = sin(lat_diff/2)**2 + cos(lat1) * cos(lat2) * sin(lon_diff/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371 if is_metric else 3956 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
        dist = c * r

        # Bearing Formula
        y = sin(lon_diff) * cos(lat2)
        x = (cos(lat1) * sin(lat2)) - (sin(lat1) * cos(lat2) * cos(lon_diff))
        theta = atan2(y, x)
        brng = (theta*180/pi + 360) % 360 # change to degrees

        return dist, brng

    # Handler to manage alternative options (metric) 
    async def distanceCogHandler(self, ctx, args, is_metric):
        locations = args.split(" to ")
        if len(locations) != 2:
            embed = discord.Embed(title='Distance Calculator', color=Colors.Error)
            embed.add_field(name=f'Expected 2 locations as arguments. Recieved {len(locations)}:', value=locations, inline=False)
            await ctx.send(embed=embed)
            return
        
        lat1, lon1, city1 = await self.getCoords(ctx, locations[0], 1)
        lat2, lon2, city2 = await self.getCoords(ctx, locations[1], 2)
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        dist, brng = self.calculateDistance(lat1, lon1, lat2, lon2, is_metric)

        field_name = f'Distance from {city1} to {city2}:'
        units = 'km' if is_metric else 'mi'
        field_value = f'{city1} is {dist:,.2f} {units} away from {city2} at an initial bearing of {brng:.2f}°!'

        embed = discord.Embed(title='Distance Calculator', color=Colors.Purple)
        embed.add_field(name=field_name, value=field_value, inline=False)
        await ctx.send(embed=embed)
        

    ##########################
    # USER EXECUTABLE COMMANDS    
    # Distance between two locations
    @ext.group(case_insensitive=True, invoke_without_command=True, aliases=['dist'])
    @ext.long_help(
        """
        This command provides the linear distance and bearing between two locations.

        Examples of locations shown below. (Both <location> tags can use different structures)
        
        Note: The format `City, ST` (ST = State Abbreviation) is **not** currently supported. 
        """
    )
    @ext.short_help('How far and what way!')
    @ext.example(('distance <location> to <location>', 'distance Clemson to Greenville', 'distance 29631 to 290601', 'dist Clemson, South Carolina to Greenville, South Carolina', \
                  'dist Clemson, SC, USA to Greenville, SC, USA', 'dist 105 Sikes Hall, Clemson, SC 29634 to 206 S Main St, Greenville, SC 29601', 'dist (34.6834, -82.8374) to (34.8526, -82.3940)'))
    async def distance(self, ctx, *, args):  # the * is used to "greedily" catch all text after it in the variable "loc"
        await self.distanceCogHandler(ctx, args, 0)

    # Distance in metric units
    @distance.command(aliases=['km'])
    @ext.long_help(
        """
        This sub-command provides the distance in metric units.
        
        Additional examples of locations provided in the `distance` command help message.
        """
    )
    @ext.short_help('Do it in Non-Freedom units.')
    @ext.example('distance metric Clemson to Greenville')
    async def metric(self, ctx, *, args):
        await self.distanceCogHandler(ctx, args, 1)

async def setup(bot):
    await bot.add_cog(DistanceCog(bot))
