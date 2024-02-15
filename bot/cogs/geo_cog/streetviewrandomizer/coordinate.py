from shapely.geometry import Point


class Coordinate:
    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon

    def within(self, polygon) -> bool:
        return Point(self.lon, self.lat).within(polygon)
