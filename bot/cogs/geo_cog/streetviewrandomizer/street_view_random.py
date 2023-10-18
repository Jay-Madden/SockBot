import bot.bot_secrets as bot_secrets
import geopandas as gpd
import logging
import random
from bot.cogs.geo_cog.streetviewrandomizer.coordinate import Coordinate
from bot.cogs.geo_cog.streetviewrandomizer.countries import COUNTRIES
from bot.cogs.geo_cog.streetviewrandomizer.street_view_static_api import StreetViewStaticApi
from dataclasses import dataclass
from io import BytesIO
from math import isclose
from PIL import Image
from timeit import default_timer as timer


"""
StreetViewRandom: runs the functionality for retrieving randomized streetview from a set of coordinates.
To view a detailed list of surveyed countries, 
run the following command before the if-statement in find_available_image():

    f'{country_df["ISO3"].values[0]} | lon: {random_lon:20} lat: {random_lat:20} | time: {elapsed_ms:8.2f}ms')
"""
API = StreetViewStaticApi()
MAX_ATTEMPTS: int = 50
IMG_PATH: str = "bot/cogs/geo_cog/temp_assets/StreetView.jpg"
ERROR: int = 101
SHAPE_FILE: str = "bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.32.shp"


# Easy way to group related data together
@dataclass
class ImageData:
    coord: Coordinate | None
    country_df: gpd.GeoDataFrame | None
    attempts: int | None
    total_elapsed_time_ms: int | None
    error_code: int | None


@dataclass
class CoordinateUrl:
    url: str
    latitude: float
    longitude: float
    iso3: str
    new_selection: list[str]


class StreetViewRandom:
    def __init__(self, args):
        self.args = args

    # Selects a random country from the list of acceptable countries
    @staticmethod
    def random_country(input_country: str) -> tuple[str, int]:
        """
        Randomly select a country, excluding ones that match the input.
        :param inputCountry: Input country to not match.
        :return: a tuple of the country and radius from the list.
        """
        country, radius = random.choice(list(COUNTRIES.items()))
        while country == input_country:
            country, radius = random.choice(list(COUNTRIES.items()))
        return country, radius

    @staticmethod
    def get_parameter(three_digit_code: str, parameter: str) -> str:
        """
        Get an image from Google Street View Static API.
        :param three_digit_code: Input ISO3 country info.
        :param parameter: The parameter to check for: iso2 or country or city.
        :return: ImageData dataclass.
        """
        gdf = gpd.read_file("bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.32.shp")
        if parameter == "iso2":
            return gdf.loc[gdf['ISO3'] == three_digit_code, 'ISO2'].squeeze()
        elif parameter == "country":
            return gdf.loc[gdf['ISO3'] == three_digit_code, 'NAME'].squeeze()
        elif parameter == "city":
            return gdf.loc[gdf['ISO3'] == three_digit_code, 'CITY_NAME'].squeeze()

    @staticmethod
    def generate_country_options() -> list[str]:
        """
        Generate a list of 5 countries which are not duplicates.
        :return: A list.
        """
        random_sample = random.sample(list(COUNTRIES.keys()), 5)
        # Convert to ISO2, check for duplicates
        iso2_conversion = [StreetViewRandom.get_parameter(x, "iso2") for x in random_sample]
        while len(iso2_conversion) != len([*set(iso2_conversion)]):
            random_sample = random.sample(list(COUNTRIES.keys()), 5)
            iso2_conversion = [StreetViewRandom.get_parameter(x, "iso2") for x in random_sample]
        return random_sample

    async def run(self, args: dict) -> CoordinateUrl:
        # Download QGIS to interact with this file
        gdf = gpd.read_file(SHAPE_FILE)
        country = args['countries'][0]
        new_country_selections_if_error = list()

        gdf = gdf.loc[gdf['ISO3'] == f"{country}"]
        gdf = gdf.assign(IMAGES=0)

        total_attempts = 0
        total_elapsed_time_ms = 0

        # Loop for the amount of samples
        for _ in range(args['samples']):
            fai = await self.find_available_image(gdf, args['radius'])
            loops: int = 0
            while fai.error_code == ERROR:
                if loops >= 1:
                    country = "SGP"
                    ro = 25
                else:
                    loop = self.generate_country_options()[0]
                    while loop in args['countries']:
                        loop = self.generate_country_options()[0]

                    country = loop
                    ro = COUNTRIES[country]

                gdf = gpd.read_file(SHAPE_FILE)
                gdf = gdf.loc[gdf['ISO3'] == f"{country}"]
                gdf = gdf.assign(IMAGES=0)
                fai = await self.find_available_image(gdf, ro)
                loops += 1

            coord = fai.coord
            country_df = fai.country_df
            attempts = fai.attempts
            elapsed_time_ms = fai.total_elapsed_time_ms
            total_attempts += attempts
            total_elapsed_time_ms += elapsed_time_ms

            country_iso3 = country_df["ISO3"].values[0]
            country_name = country_df["NAME"].values[0]
            gdf.loc[gdf["ISO3"] == country_iso3, "IMAGES"] += 1

            logging.log(1, f"\n> Image found in {country_iso3} ({country_name}) | "
                           f"lon: {coord.lon}, lat: {coord.lat} | attempts: {attempts} "
                           f"| total elapsed time: {elapsed_time_ms / 1000:.2f}s\n")
            total_elapsed_time_ms = total_elapsed_time_ms + int(await self.save_images(
                coord, args['size'], args['headings'], args['pitches'], args['fovs']
            ))
            logging.log(1, f"\nImage saved!\n Total attempts: {total_attempts} Average number of attempts per "
                           f"sampling: {total_attempts / args['samples']:.2f} "
                           f"\nTotal elapsed time: {total_elapsed_time_ms / 1000:.2f}s Average elapsed time per "
                           f"sampling: "
                           f"{(total_elapsed_time_ms / 1000) / args['samples']:.2f}s")

        size = args['size']

        return CoordinateUrl(('https://maps.googleapis.com/maps/api/streetview?'
                + f'size={size}&'
                + f'location={coord.lat},{coord.lon}&'
                + f"heading={args['headings']}&"
                + f"pitch={args['pitches']}&"
                + f"fov={args['fovs']}&"
                + f"key={bot_secrets.secrets.geocode_key}"),
                coord.lat,
                coord.lon,
                country_iso3,
                new_country_selections_if_error)

    @staticmethod
    def compute_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        gdf = gdf.eval("AREA = geometry.to_crs('esri:54009').area")
        gdf = gdf.sort_values(by="AREA", ascending=False)

        gdf = gdf.eval("AREA_PERCENTAGE = AREA / AREA.sum()")
        gdf = gdf.sort_values(by="AREA_PERCENTAGE", ascending=False)
        gdf = gdf.reset_index(drop=True)

        return gdf

    # Find a random point in the specified country up to 50 times or until street view is found.
    async def find_available_image(self, gdf: gpd.GeoDataFrame, radius_m: int) -> ImageData:
        """
        Get an image from Google Street View Static API.
        :param gdf: Geo-dataframe for a single target country.
        :param radius_m: Grab the nearest streetview within a radius.
        :return: ImageData dataclass.
        """
        coord: Coordinate
        country_df = None
        attempts = 0
        total_elapsed_time_ms = 0
        image_found = False

        while True:
            start = timer()
            attempts += 1
            country_df = self.get_random_country(gdf)
            min_lon, min_lat, max_lon, max_lat = country_df.total_bounds
            random_lat = random.uniform(min_lat, max_lat)
            random_lon = random.uniform(min_lon, max_lon)

            random_lat = 27.98812003113945 if isclose(27.98812003113945, random_lat, abs_tol=10**-4) else random_lat
            random_lon = 86.92497299755392 if isclose(86.92497299755392, random_lon, abs_tol=10**-4) else random_lon
            radius_m = 1000 if isclose(86.92497299755392, random_lon, abs_tol=10**-4) else radius_m

            logging.log(1, f"\n{attempts}")
            coord = Coordinate(random_lat, random_lon)
            status: str = ""

            if attempts >= MAX_ATTEMPTS:
                logging.warning(f"\nMaximum safe attempts ({MAX_ATTEMPTS}) exceeded. Choosing a different country.")
                return ImageData(None, None, None, None, ERROR)

            if coord.within(country_df.geometry.values[0]):
                coord, status = await API.has_image(coord, radius_m)

            end = timer()
            elapsed_ms = (end - start) * 1000
            total_elapsed_time_ms += elapsed_ms

            if status == "OK":
                break

            if image_found:
                break

        return ImageData(coord, country_df, attempts, total_elapsed_time_ms, 0)

    # Uses the sample function to get a random row from the data table
    @staticmethod
    def get_random_country(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Scan through shapefile for a random country. In this case it's grabbing
        area data from a single country.
        :param gdf - input geo-dataframe
        :return: A geo-dataframe.
        """
        return gdf.sample(n=1, weights="AREA_PERCENTAGE" if "AREA_PERCENTAGE" in gdf.columns else None)

    # Save the found image in the specified path
    @staticmethod
    async def save_images(coord: Coordinate, size: str, headings: int, pitches: int, fovs: int) -> int:
        """
        Get an image from Google Street View Static API.
        :param coord: Coordinate.
        :param size: Image size.
        :param headings: Heading, defaults to 180.
        :param pitches: Pitch, defaults to 0.
        :param fovs: Field of view, defaults to 110.
        :return: Elapsed time in microsecs.
        """
        start = timer()

        img: bytes = await API.get_image(coord, size, heading=headings, pitch=pitches, fov=fovs)
        img: bytes = Image.open(BytesIO(img))

        img.save(IMG_PATH)

        end = timer()
        total_elapsed_time_ms = (end - start) * 1000

        return int(total_elapsed_time_ms)
