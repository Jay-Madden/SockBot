import aiohttp
import asyncio
from bot.cogs.geo_cog.streetviewrandomizer.coordinate import Coordinate
import bot.bot_secrets as bot_secrets
import nest_asyncio
import json
import logging

endpoint = "https://maps.googleapis.com/maps/api/streetview"
session = aiohttp.ClientSession()
nest_asyncio.apply()


class StreetViewStaticApi:
    async def close_session(self):
        if not self.session.closed:
            await self.session.close()

    def has_image(self, coord: Coordinate, radius_m: int) -> tuple[bool, Coordinate]:
        """
        Check if the API key exists.
        """
        if bot_secrets.secrets.geocode_key is None:
            raise Exception("API key is required. Use --api-key or set the GOOGLE_MAPS_API_KEY environment variable.")
        """
        Check if the location has an image.
        :param `coord`: Coordinate.
        :param `radius_m`: Radius (in meters) to search for an image.
        :return: Tuple containing a boolean indicating if an image was found and the coordinate.
        """
        async def getThing():
            async with session.get(url=f"{endpoint}/metadata", params={"location": f"{coord.lat},{coord.lon}",
                                                                       "key": bot_secrets.secrets.geocode_key,
                                                                       "radius": radius_m},
                                   allow_redirects=False) as resp:
                return json.loads(await resp.text())

        loop = asyncio.get_running_loop()
        response = asyncio.get_event_loop().run_until_complete( getThing() )

        image_found = response["status"] == "OK"

        if response["status"] == "OVER_QUERY_LIMIT":
            logging.warning("You have exceeded your daily quota or per-second quota for this API.")
            image_found = False

        if response["status"] == "REQUEST_DENIED":
            logging.warning("Your request was denied by the server. Check your API key.")
            image_found = False

        if response["status"] == "UNKNOWN_ERROR":
            logging.warning("An unknown error occurred on the server.")
            image_found = False

        if "location" in response:
            lat = response["location"]["lat"]
            lon = response["location"]["lng"]
            coord = Coordinate(lat, lon)

        self.close_session()
        return image_found, coord

    def get_image(self, coord: Coordinate, size: str, heading=180, pitch=0, fov=110) -> bytes:
        """
        Get an image from Google Street View Static API.
        :param `coord`: Coordinate.
        :param `size`: Image size.
        :param `heading`: Heading, defaults to 180.
        :param `pitch`: Pitch, defaults to 0.
        :param `fov`: Field of view, defaults to 110.
        :return: Image in bytes.
        """
        async def getThing():
            async with session.get(url=endpoint,
                                   params={"location": f"{coord.lat},{coord.lon}", "size": size, "heading": heading,
                                           "pitch": pitch, "fov": fov, "key": bot_secrets.secrets.geocode_key},
                                   allow_redirects=False) as resp:
                return await resp.read()
        response = asyncio.get_event_loop().run_until_complete( getThing() )
        self.close_session()
        return response


