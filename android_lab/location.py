from __future__ import annotations

import csv
import math
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

from .adb import Adb


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float
    elevation: float = 0

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.lat, self.lon, self.elevation)):
            raise ValueError("Location values must be finite")
        if not -90 <= self.lat <= 90 or not -180 <= self.lon <= 180:
            raise ValueError("Location outside latitude/longitude range")


def read_gpx(path: Path) -> list[Point]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f'Invalid GPX XML: {exc}') from exc
    # Prefer track points, then route points, then standalone waypoints.
    for kind in ("trkpt", "rtept", "wpt"):
        nodes = [n for n in root.iter() if n.tag.rsplit('}', 1)[-1] == kind]
        if nodes:
            points = []
            for node in nodes:
                try:
                    elevation = next((float(n.text) for n in node if n.tag.rsplit('}', 1)[-1] == 'ele'), 0)
                    points.append(Point(float(node.attrib['lat']), float(node.attrib['lon']), elevation))
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f'Invalid GPX coordinate: {exc}') from exc
            return points
    raise ValueError("GPX has no track, route, or waypoint coordinates")


def distance(a: Point, b: Point) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat, dlon = lat2 - lat1, math.radians(b.lon - a.lon)
    hav = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 6371000 * 2 * math.asin(math.sqrt(min(1, max(0, hav))))


def updates(points: list[Point], speed: float, interval: float = 1):
    if not points or not math.isfinite(speed) or speed <= 0 or not math.isfinite(interval) or interval <= 0:
        raise ValueError("A route and positive finite speed/interval are required")
    yield points[0], 0.0
    for a, b in zip(points, points[1:]):
        duration = distance(a, b) / speed
        if duration == 0:
            continue
        count = max(1, math.ceil(duration / interval))
        delta_lon = (b.lon - a.lon + 180) % 360 - 180
        for i in range(1, count + 1):
            fraction = i / count
            # Linear interpolation suits short QA routes; wrap at the date line.
            point = b if i == count else Point(a.lat + (b.lat-a.lat)*fraction,
                (a.lon + delta_lon*fraction + 180) % 360 - 180,
                a.elevation + (b.elevation-a.elevation)*fraction)
            yield point, duration / count


def set_location(adb: Adb, point: Point) -> None:
    result = str(adb.run('emu', 'geo', 'fix', str(point.lon), str(point.lat), str(point.elevation)))
    if 'OK' not in result or 'KO' in result:
        raise RuntimeError(f"Emulator rejected location: {result}")


def follow(adb: Adb, path: Path, speed: float, trace: Path) -> None:
    points = read_gpx(path)
    sequence = updates(points, speed)
    # Validate the speed before opening an existing output file.
    first = next(sequence)
    trace.parent.mkdir(parents=True, exist_ok=True)
    with trace.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['timestamp', 'lat', 'lon', 'speed_mps'])
        scheduled = time.monotonic()
        for point, delay in chain((first,), sequence):
            scheduled += delay
            time.sleep(max(0, scheduled - time.monotonic()))
            set_location(adb, point)
            writer.writerow([time.time(), point.lat, point.lon, speed])
            stream.flush()
