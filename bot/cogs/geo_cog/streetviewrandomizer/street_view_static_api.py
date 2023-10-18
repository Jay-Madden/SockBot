import aiohttp as aiohttp
import bot.bot_secrets as bot_secrets
import json
import logging
import nest_asyncio
from bot.cogs.geo_cog.streetviewrandomizer.coordinate import Coordinate
from timeit import default_timer as timer

ENDPOINT = "https://maps.googleapis.com/maps/api/streetview"
SESSION = aiohttp.ClientSession()
nest_asyncio.apply()


class StreetViewStaticApi:

    @staticmethod
    async def geolocate(quota: int, pic_base: str, filename: str, location_params: dict) -> tuple[str, float]:
        start = timer()
        if quota > 0:
            curr_session = aiohttp.ClientSession()
            async with curr_session.get(url=pic_base,
                                        params=location_params,
                                        allow_redirects=False) as resp:
                pic_response = await resp.read()
                f = open(f'bot/cogs/geo_cog/temp_assets/{filename}', 'wb')
                f.write(pic_response)
                f.close()

                end = timer()
                api_rest_time = (end - start) * 1000
                return filename, api_rest_time

    @staticmethod
    async def has_image(coord: Coordinate, radius_m: int) -> tuple[Coordinate, bool]:
        """
        Check if the location has an image.
        :param coord: Coordinate.
        :param radius_m: Radius (in meters) to search for an image.
        :return: Tuple containing a boolean indicating if an image was found and the coordinate.
        """
        async with SESSION.get(url=f"{ENDPOINT}/metadata", params={"location": f"{coord.lat},{coord.lon}",
                                                                   "key": bot_secrets.secrets.geocode_key,
                                                                   "radius": radius_m},
                               allow_redirects=False) as resp:
            response = json.loads(await resp.text())

            if response["status"] == "OVER_QUERY_LIMIT":
                logging.warning("You have exceeded your daily quota or per-second quota for this API.")

            if response["status"] == "REQUEST_DENIED":
                logging.warning("Your request was denied by the server. Check your API key.")

            if response["status"] == "UNKNOWN_ERROR":
                logging.warning("An unknown error occurred on the server.")

            if 'location' in response:
                lat = response["location"]["lat"]
                lon = response["location"]["lng"]
                coord = Coordinate(lat, lon)

            return coord, response["status"]

    @staticmethod
    async def get_image(coord: Coordinate, size: str, heading=180, pitch=0, fov=110) -> bytes:
        """
        Get an image from Google Street View Static API.
        :param coord: Coordinate.
        :param size: Image size.
        :param heading: Heading, defaults to 180.
        :param pitch: Pitch, defaults to 0.
        :param fov: Field of view, defaults to 110.
        :return: Image in bytes.
        """
        async with SESSION.get(url=ENDPOINT,
                               params={"location": f"{coord.lat},{coord.lon}", "size": size, "heading": heading,
                                       "pitch": pitch, "fov": fov, "key": bot_secrets.secrets.geocode_key},
                               allow_redirects=False) as resp:

            response = await resp.read()
            return response
