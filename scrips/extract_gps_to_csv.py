#!/usr/bin/env python3
"""
Extrahiert GPS-Koordinaten aus Bildern in einem Ordner und schreibt
Dateiname, Breitengrad und Längengrad in eine CSV-Datei.

Unterstützte Formate hängen von Pillow ab, typischerweise z. B. JPG/JPEG/TIFF.

Beispiel:
    python extract_gps_to_csv.py /pfad/zum/bilderordner -o gps_daten.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Mapping, Optional

from PIL import ExifTags, Image


GPS_TAG = next((tag for tag, name in ExifTags.TAGS.items() if name == "GPSInfo"), None)
GPS_SUBTAGS = ExifTags.GPSTAGS


def rational_to_float(value) -> float:
    """Wandelt EXIF-Rational-Werte robust in float um."""
    try:
        return float(value)
    except (TypeError, ValueError):
        pass

    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return value.numerator / value.denominator

    if isinstance(value, tuple) and len(value) == 2:
        num, den = value
        return float(num) / float(den)

    raise ValueError(f"Unbekannter Rational-Wert: {value!r}")


def dms_to_decimal(dms, ref: str) -> float:
    """Wandelt Grad/Minuten/Sekunden in Dezimalgrad um."""
    if len(dms) != 3:
        raise ValueError(f"Ungültiger GPS-DMS-Wert: {dms!r}")

    degrees = rational_to_float(dms[0])
    minutes = rational_to_float(dms[1])
    seconds = rational_to_float(dms[2])

    if not all(math.isfinite(value) for value in (degrees, minutes, seconds)):
        raise ValueError(f"Ungültiger GPS-DMS-Wert: {dms!r}")

    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

    if ref in {"S", "W"}:
        decimal *= -1

    return decimal


def get_gps_ifd(exif) -> Optional[Mapping]:
    """Liest das GPS-IFD aus Pillow-EXIF-Daten."""
    if GPS_TAG is None:
        return None

    if hasattr(exif, "get_ifd"):
        gps_ifd = exif.get_ifd(GPS_TAG)
        if gps_ifd:
            return gps_ifd

    gps_ifd = exif.get(GPS_TAG)
    if isinstance(gps_ifd, Mapping):
        return gps_ifd

    return None


def extract_gps(image_path: Path) -> tuple[Optional[float], Optional[float]]:
    """Liest GPS-Daten aus einem Bild aus. Gibt (lat, lon) oder (None, None) zurück."""
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                return None, None

            gps_info_raw = get_gps_ifd(exif)
            if not gps_info_raw:
                return None, None

            gps_info = {}
            for key, value in gps_info_raw.items():
                decoded_key = GPS_SUBTAGS.get(key, key)
                gps_info[decoded_key] = value

            lat = gps_info.get("GPSLatitude")
            lat_ref = gps_info.get("GPSLatitudeRef")
            lon = gps_info.get("GPSLongitude")
            lon_ref = gps_info.get("GPSLongitudeRef")

            if not all([lat, lat_ref, lon, lon_ref]):
                return None, None

            if lat_ref not in {"N", "S"} or lon_ref not in {"E", "W"}:
                return None, None

            latitude = dms_to_decimal(lat, lat_ref)
            longitude = dms_to_decimal(lon, lon_ref)
            return latitude, longitude

    except Exception as exc:
        print(f"Warnung: {image_path.name} konnte nicht verarbeitet werden: {exc}", file=sys.stderr)
        return None, None


def iter_images(folder: Path):
    """Iteriert rekursiv über wahrscheinliche Bilddateien."""
    allowed_suffixes = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".webp"}
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in allowed_suffixes:
            yield path


def write_csv(input_folder: Path, output_csv: Path, include_empty: bool = False) -> None:
    rows_written = 0
    files_seen = 0
    files_without_gps = 0

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["dateiname", "breitengrad", "laengengrad"])

        for image_path in iter_images(input_folder):
            files_seen += 1
            lat, lon = extract_gps(image_path)

            if lat is None or lon is None:
                files_without_gps += 1
                if include_empty:
                    writer.writerow([image_path.name, "", ""])
                    rows_written += 1
                continue

            writer.writerow([image_path.name, f"{lat:.8f}", f"{lon:.8f}"])
            rows_written += 1

    print(f"Fertig. {rows_written} Zeilen nach '{output_csv}' geschrieben.")
    print(f"Geprüfte Bilddateien: {files_seen}")
    if files_without_gps:
        print(f"Ohne verwertbare GPS-Koordinaten: {files_without_gps}")
    if rows_written == 0 and files_seen:
        print("Hinweis: Die geprüften Bilder enthalten keine auslesbaren GPS-Koordinaten.")
        print("Mit --include-empty werden die Dateinamen trotzdem in die CSV geschrieben.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrahiert GPS-Koordinaten aus Bildern und schreibt sie in eine CSV-Datei."
    )
    parser.add_argument(
        "input_folder",
        type=Path,
        help="Ordner mit Bildern",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("gps_koordinaten.csv"),
        help="Pfad zur Ausgabe-CSV (Standard: gps_koordinaten.csv)",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Schreibt auch Bilder ohne GPS-Daten in die CSV, mit leeren Koordinatenfeldern.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input_folder.exists() or not args.input_folder.is_dir():
        print(f"Fehler: '{args.input_folder}' ist kein gültiger Ordner.", file=sys.stderr)
        return 1

    try:
        write_csv(args.input_folder, args.output, include_empty=args.include_empty)
        return 0
    except KeyboardInterrupt:
        print("Abgebrochen.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
