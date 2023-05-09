import random
from io import BytesIO
from timeit import default_timer as timer
import geopandas as gpd
import logging
import bot.bot_secrets as bot_secrets
from PIL import Image
from dataclasses import dataclass
from bot.cogs.geo_cog.streetviewrandomizer.street_view_static_api import StreetViewStaticApi
from bot.cogs.geo_cog.streetviewrandomizer.coordinate import Coordinate
from bot.cogs.geo_cog.streetviewrandomizer.countries import Countries

"""
StreetViewRandom: runs the functionality for retrieving randomized streetview from a set of coordinates.
To view a detailed list of surveyed countries, 
run the following command before the if-statement in find_available_image():

    f'{country_df["ISO3"].values[0]} | lon: {random_lon:20} lat: {random_lat:20} | time: {elapsed_ms:8.2f}ms')
"""
API = StreetViewStaticApi()
MAX_ATTEMPTS = 50
img_path = f"bot/cogs/geo_cog/tempAssets/StreetView.jpg"
Error: int = 101
shape_file = "bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp"


# Easy way to group related data together
@dataclass()
class ImageData:
    coord: Coordinate
    country_df: gpd.GeoDataFrame
    attempts: int
    total_elapsed_time_ms: int
    error_code: int


class StreetViewRandom:
    def __init__(self, args):
        self.args = args

    # Selects a random country from the list of acceptable countries
    @staticmethod
    def random_country(inputCountry: str):
        c, r = random.choice(list(Countries.items()))
        while c == inputCountry:
            c, r = random.choice(list(Countries.items()))
        return c, r

    def run(self, args) -> tuple:
        global API
        # Download QGIS to interact with this file
        gdf = gpd.read_file("bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp")
        country = args['countries']

        gdf = gdf.loc[gdf['ISO3'] == f"{country}"]
        gdf = gdf.assign(IMAGES=0)

        total_attempts = 0
        total_elapsed_time_ms = 0

        # Loop for the amount of samples
        for i in range(args['samples']):
            FAI = self.find_available_image(gdf, args['radius'])
            catchError = FAI.error_code
            loops = 0
            while catchError == Error:
                if loops >= 1:
                    logging.warning("Too many attempts (100+), defaulting to Singapore.")
                    country = "SGP"
                    ro = 25
                else:
                    country, ro = self.random_country(country)
                gdf = gpd.read_file(shape_file)
                gdf = gdf.loc[gdf['ISO3'] == f"{country}"]
                gdf = gdf.assign(IMAGES=0)
                FAI = self.find_available_image(gdf, ro)
                catchError = FAI.error_code
                loops += 1

            coord = FAI.coord
            country_df = FAI.country_df
            attempts = FAI.attempts
            elapsed_time_ms = FAI.total_elapsed_time_ms
            total_attempts += attempts
            total_elapsed_time_ms += elapsed_time_ms

            country_iso3 = country_df["ISO3"].values[0]
            country_name = country_df["NAME"].values[0]
            gdf.loc[gdf["ISO3"] == country_iso3, "IMAGES"] += 1

            print(
             f"\n> Image found in {country_iso3} ({country_name}) | "
             f"lon: {coord.lon}, lat: {coord.lat} | attempts: {attempts} "
             f"| total elapsed time: {elapsed_time_ms / 1000:.2f}s"
            )
            print("\nImage found now save\n")
            total_elapsed_time_ms = total_elapsed_time_ms + int(self.save_images(
                coord, args['size'], args['headings'], args['pitches'], args['fovs']
            ))
            logging.info(f"\nImage saved!\n Total attempts: {total_attempts} Average number of attempts per "
                  f"sampling: {total_attempts / args['samples']:.2f} "
                  f"\nTotal elapsed time: {total_elapsed_time_ms / 1000:.2f}s Average elapsed time per sampling: "
                  f"{(total_elapsed_time_ms / 1000) / args['samples']:.2f}s")

        SIZE = args['size']

        return (('https://maps.googleapis.com/maps/api/streetview?'
                + f'size={SIZE}&'
                + f'location={coord.lat},{coord.lon}&'
                + f"heading={args['headings']}&"
                + f"pitch={args['pitches']}&"
                + f"fov={args['fovs']}&"
                + f"key={bot_secrets.secrets.geocode_key}"),
                coord.lat,
                coord.lon,
                country_iso3)

    @staticmethod
    def compute_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        gdf = gdf.eval("AREA = geometry.to_crs('esri:54009').area")
        gdf = gdf.sort_values(by="AREA", ascending=False)

        gdf = gdf.eval("AREA_PERCENTAGE = AREA / AREA.sum()")
        gdf = gdf.sort_values(by="AREA_PERCENTAGE", ascending=False)
        gdf = gdf.reset_index(drop=True)

        return gdf

    # Find a random point in the specified country up to 50 times or until street view is found.
    def find_available_image(self, gdf: gpd.GeoDataFrame, radius_m: int) -> ImageData:
        global Error
        coord = None
        country_df = None
        attempts = 0
        total_elapsed_time_ms = 0
        image_found = False

        while not image_found:
            start = timer()
            attempts += 1
            country_df = self.get_random_country(gdf)
            min_lon, min_lat, max_lon, max_lat = country_df.total_bounds
            random_lat = random.uniform(min_lat, max_lat)
            random_lon = random.uniform(min_lon, max_lon)
            coord = Coordinate(random_lat, random_lon)

            if attempts >= MAX_ATTEMPTS:
                logging.warning("Maximum safe attempts (50) exceeded. Choosing a different country.")
                returnValue: ImageData = ImageData(Error, Error, Error, Error, Error)
                return returnValue

            if coord.within(country_df.geometry.values[0]):
                image_found, coord = API.has_image(coord, radius_m)

            end = timer()
            elapsed_ms = (end - start) * 1000
            total_elapsed_time_ms += elapsed_ms

            if image_found:
                break

        returnValue: ImageData = ImageData(coord, country_df, attempts, total_elapsed_time_ms, 0)
        return returnValue

    # Uses the sample function to get a random row from the data table
    @staticmethod
    def get_random_country(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        return gdf.sample(n=1, weights="AREA_PERCENTAGE" if "AREA_PERCENTAGE" in gdf.columns else None)

    # Save the found image in the specified path
    @staticmethod
    def save_images(coord: Coordinate, size: str, headings: int, pitches: int, fovs: int) -> int:
        start = timer()

        img: bytes = API.get_image(coord, size, heading=headings, pitch=pitches, fov=fovs)

        img: bytes = Image.open(BytesIO(img))

        img.save(img_path)

        end = timer()
        total_elapsed_time_ms = (end - start) * 1000
        return int(total_elapsed_time_ms)
