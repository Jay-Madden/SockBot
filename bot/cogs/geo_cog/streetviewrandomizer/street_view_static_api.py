from bot.cogs.geo_cog.streetviewrandomizer.coordinate import Coordinate
import asyncio
import bot.bot_secrets as bot_secrets
import nest_asyncio
import json
import logging
from timeit import default_timer as timer
import aiohttp as aiohttp

ENDPOINT = "https://maps.googleapis.com/maps/api/streetview"
SESSION = aiohttp.ClientSession()
nest_asyncio.apply()


class StreetViewStaticApi:

    @staticmethod
    async def geolocate(quota: int, pic_base: str, filename: str, location_params: str) -> tuple[str, float]:
        start = timer()
        if quota > 0:
            curr_session = aiohttp.ClientSession()
            await asyncio.sleep(1)
            async with curr_session.get(url=pic_base,
                                        params=location_params,
                                        allow_redirects=False) as resp:
                pic_response = await resp.read()
                await curr_session.close()
                await asyncio.sleep(1)
                f = open(f'bot/cogs/geo_cog/temp_assets/{filename}', 'wb')
                f.write(pic_response)
                f.close()

                end = timer()
                api_rest_time = (end - start) * 1000
                return filename, api_rest_time

    @staticmethod
    async def has_image(coord: Coordinate, radius_m: int) -> dict[str]:
        """
        Check if the API key exists.
        """
        if bot_secrets.secrets.geocode_key is None:
            raise Exception("API key is required. Use --api-key or set the GOOGLE_MAPS_API_KEY environment variable.")
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

            return response

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

            await asyncio.sleep(1)

            return response
