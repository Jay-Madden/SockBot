import requests
from bot.cogs.geo_cog.streetviewrandomizer.coordinate import Coordinate
import bot.bot_secrets as bot_secrets

class StreetViewStaticApi:
    def __init__(self, api_key: str):
        self.endpoint = "https://maps.googleapis.com/maps/api/streetview"

        if api_key is None:
            raise Exception("API key is required. Use --api-key or set the GOOGLE_MAPS_API_KEY environment variable.")

        self.api_key = api_key

    def has_image(self, coord: Coordinate, radius_m: int) -> tuple((bool, Coordinate)):
        """
        Check if the location has an image.
        :param `coord`: Coordinate.
        :param `radius_m`: Radius (in meters) to search for an image.
        :return: Tuple containing a boolean indicating if an image was found and the coordinate.
        """
        response = requests.get(
            f"{self.endpoint}/metadata",
            params={
                "location": f"{coord.lat},{coord.lon}",
                "key": self.api_key,
                "radius": radius_m
            },
        ).json()

        if response["status"] == "OVER_QUERY_LIMIT":
            raise Exception("You have exceeded your daily quota or per-second quota for this API.")

        if response["status"] == "REQUEST_DENIED":
            raise Exception("Your request was denied by the server. Check your API key.")

        if response["status"] == "UNKNOWN_ERROR":
            raise Exception("An unknown error occurred on the server.")

        image_found = response["status"] == "OK"

        if "location" in response:
            lat = response["location"]["lat"]
            lon = response["location"]["lng"]
            coord = Coordinate(lat, lon)

        return image_found, coord

    def get_image(self, coord: Coordinate, size: str, heading=180, pitch=0, fov=110) -> bytes:
        """
        Get an image from Google Street View Static API.
        :param `coord`: Coordinate.
        :param `size`: Image size.
        :param `heading`: Heading, defaults to 0.
        :param `pitch`: Pitch, defaults to 0.
        :param `fov`: Field of view, defaults to 90.
        :return: Image in bytes.
        """

        response = requests.get(
            self.endpoint,
            params={
                "location": f"{coord.lat},{coord.lon}",
                "size": size,
                "heading": heading,
                "pitch": pitch,
                "fov": fov,
                "key": self.api_key
            },
        )

        return response.content