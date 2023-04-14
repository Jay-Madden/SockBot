import os
import random
from io import BytesIO
from timeit import default_timer as timer
import geopandas as gpd
from PIL import Image
from bot.cogs.geo_cog.streetviewrandomizer.countries import countries_codes
from bot.cogs.geo_cog.streetviewrandomizer.street_view_static_api import StreetViewStaticApi
from bot.cogs.geo_cog.streetviewrandomizer.coordinate import Coordinate

class StreetViewRandom:
    def __init__(self, args):
        self.args = args

    Error: str = 101
    Countries = {"USA": 1250, "FRA": 250, "ESP": 200,
                 "TWN": 70,   "SVK": 50,  "POL": 100,
                 "IRL": 75,   "LVA": 150, "SGP": 25,
                 "ITA": 100,  "CZE": 100, "RUS": 2500,
                 "BGD": 150,  "SMR": 15,  "JPN": 250,
                 "BRA": 2000, "BGR": 100, "BLL": 10,
                 "CWN": 10,   "SPO": 10, "BOO": 10,
                 "ATL": 15,   "TOT": 10, "DET": 15,
                 "PJT": 20,   "PXA": 4,  "TKY": 10,
                 "TLL": 10,   "AAA": 20, "MMM": 20,
                 "HST": 20,   "PWJ": 10, "STD": 15,
                 "MSW": 30,   "CBA": 15
                 }

    @staticmethod
    def random_country(self, input):
        print("Error location 2")
        c, r = random.choice(list(StreetViewRandom.Countries.items()))
        print("Error location 3")
        while (c == input):
            c, r = random.choice(list(StreetViewRandom.Countries.items()))
        print(f"new country {c}")
        return c, r

    def run(self, args):
        global API

        API = StreetViewStaticApi(args['api_key'])

        gdf = gpd.read_file("bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp")
        f = open("bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/transcribedData.txt", "a")
        f.write("   FIPS ISO2 ISO3   UN   NAME   AREA    POP2005  REGION  SUBREGION      LON     LAT                                           geometry")

        print(gdf.loc[gdf['ISO3'] == "BLN"])

        country = args['countries']
        if country.upper() not in countries_codes["iso3"]:
            print(f'Bad country ISO3 code: "{country}"')
            print("Run with option -l to list all available countries")
            return

        #gdf = gdf.query(f"ISO3 in {country}")
        gdf = gdf.loc[gdf['ISO3'] == f"{country}"]
        print(gdf.head())
        gdf = gdf.assign(IMAGES=0)

        #total_images_per_country = len(args['headings']) * len(args['pitches']) * len(args['fovs'])
        total_attempts = 0
        total_elapsed_time_ms = 0
        catchError = 0

        for i in range(args['samples']):
            print(f"\n{'-' * 40} Sampling {i + 1}/{args['samples']} {'-' * 40}\n")
            FAI = self.find_available_image(gdf, args['radius'], self.Error)
            catchError = FAI[4]
            loops = 0
            while catchError == self.Error:
                if loops >= 1:
                    country = "SGP"
                    ro = 25
                else:
                    country, ro = self.random_country(self, country)
                gdf = gpd.read_file("bot/cogs/geo_cog/streetviewrandomizer/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp")
                gdf = gdf.loc[gdf['ISO3'] == f"{country}"]
                gdf = gdf.assign(IMAGES=0)
                FAI = self.find_available_image(gdf, ro, self.Error)
                catchError = FAI[4]
                loops += 1

            coord, country_df, attempts, elapsed_time_ms, catchError = FAI

            total_attempts += attempts
            total_elapsed_time_ms += elapsed_time_ms

            country_iso3 = country_df["ISO3"].values[0]
            country_name = country_df["NAME"].values[0]
            gdf.loc[gdf["ISO3"] == country_iso3, "IMAGES"] += 1

            print(
             f"\n> Image found in {country_iso3} ({country_name}) | lon: {coord.lon}, lat: {coord.lat} | attempts: {attempts} | total elapsed time: {elapsed_time_ms / 1000:.2f}s"
            )
            print("\nImage found now save\n")
            total_elapsed_time_ms = total_elapsed_time_ms + int(self.save_images(
                country_iso3, coord, args['output_dir'], args['size'], args['headings'], args['pitches'], args['fovs']
            ) )
            print("\nImage successfully saved\n")

            print(f"\nTotal attempts: {total_attempts}")
            print(f"Average number of attempts per sampling: {total_attempts / args['samples']:.2f}")

            print(f"\nTotal elapsed time: {total_elapsed_time_ms / 1000:.2f}s")
            print(f"Average elapsed time per sampling: {(total_elapsed_time_ms / 1000) / args['samples']:.2f}s")
        SIZE = args['size']
        returnVals = {'URL': ('https://maps.googleapis.com/maps/api/streetview?'
                               + f'size={SIZE}&'
                               + f'location={coord.lat},{coord.lon}&'
                               + f"heading={args['headings']}&"
                               + f"pitch={args['pitches']}&"
                               + f"fov={args['fovs']}&"
                               + f"key={args['api_key']}"
                               ),
                        'lat': coord.lat,
                        'lon': coord.lon,
                        'ISO3Digits': country_iso3}
        return returnVals

    def compute_area(self, gdf: gpd.GeoDataFrame):
        gdf = gdf.eval("AREA = geometry.to_crs('esri:54009').area")
        gdf = gdf.sort_values(by="AREA", ascending=False)

        # Antarctica is huge, but its Google Street View coverage is very small.
        # Thus, we reduce its area so as to avoid picking it too often.
        gdf.loc[gdf["ISO3"] == "ATA", "AREA"] = gdf["AREA"].min()

        gdf = gdf.eval("AREA_PERCENTAGE = AREA / AREA.sum()")
        gdf = gdf.sort_values(by="AREA_PERCENTAGE", ascending=False)
        gdf = gdf.reset_index(drop=True)

        return gdf

    def find_available_image(self, gdf: gpd.GeoDataFrame, radius_m, error_code):
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

            if attempts >= 50:
                return (self.Error, self.Error, self.Error, self.Error, error_code)

            if coord.within(country_df.geometry.values[0]):
                image_found, coord = API.has_image(coord, radius_m)

            end = timer()
            elapsed_ms = (end - start) * 1000
            total_elapsed_time_ms += elapsed_ms

            print(
                f'Searched image in {country_df["ISO3"].values[0]} | lon: {random_lon:20} lat: {random_lat:20} | elapsed time: {elapsed_ms:8.2f}ms'
            )

            if image_found:
                break
        # wrap in () in case broken
        return coord, country_df, attempts, total_elapsed_time_ms, 0

    def get_random_country(self, gdf: gpd.GeoDataFrame):
        return gdf.sample(n=1, weights="AREA_PERCENTAGE" if "AREA_PERCENTAGE" in gdf.columns else None)

    def save_images(self, iso3_code: str, coord: Coordinate, output_dir, size, headings, pitches, fovs):
        if output_dir.endswith("/"):
            output_dir = output_dir[:-1]

        output_dir += f"/{iso3_code.lower()}"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        count = 0
        start = timer()

        count += 1
        img = API.get_image(coord, size, heading=headings, pitch=pitches, fov=fovs)

        img = Image.open(BytesIO(img))

        img_path = f"bot/cogs/geo_cog/tempAssets/StreetView.jpg"
        img.save(img_path)

        end = timer()
        total_elapsed_time_ms = (end - start) * 1000
        print("ok we got here atleast right?")
        return total_elapsed_time_ms
