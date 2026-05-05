#!/usr/bin/env python3
"""Liest eine CSV ein und erzeugt daraus eine XML- und JSON-Datei.

Erwartete CSV-Spalten:
- dateiname
- breitengrad
- laengengrad
- titel

Optional unterstützte Spalten:
- id
- address
- description
- links

Falls optionale Spalten fehlen, werden Standardwerte verwendet.

Die Spalte `links` kann mehrere Links enthalten, getrennt durch `|` oder `;`.
Wenn `links` fehlt, wird standardmäßig `dateiname` als einzelner Link verwendet.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring


DEFAULT_DESCRIPTION = (
    '<p>Automatisch aus CSV erzeugter Eintrag.</p>'
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Erzeugt aus einer CSV eine rooms.xml und rooms.json."
    )
    parser.add_argument("input_csv", help="Pfad zur Eingabe-CSV")
    parser.add_argument(
        "-x",
        "--xml-output",
        default="rooms.xml",
        help="Pfad zur XML-Ausgabedatei (Standard: rooms.xml)",
    )
    parser.add_argument(
        "-j",
        "--json-output",
        default="rooms.json",
        help="Pfad zur JSON-Ausgabedatei (Standard: rooms.json)",
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="CSV-Trennzeichen (Standard: ,)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Zeichenkodierung der CSV (Standard: utf-8-sig)",
    )
    parser.add_argument(
        "--default-address",
        default="",
        help="Standardwert für <address>, falls keine Spalte 'address' vorhanden ist",
    )
    parser.add_argument(
        "--default-description",
        default=DEFAULT_DESCRIPTION,
        help="Standardwert für <description>, falls keine Spalte 'description' vorhanden ist",
    )
    parser.add_argument(
        "--link-prefix",
        default="",
        help="Optionales Präfix für Links aus der Spalte 'dateiname', z. B. /fileadmin/.../",
    )
    return parser.parse_args()


def normalize_fieldnames(fieldnames: List[str]) -> List[str]:
    return [name.strip().lower() for name in fieldnames]


def split_links(value: str) -> List[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    separator = "|" if "|" in raw else ";" if ";" in raw else None
    if separator is None:
        return [raw]
    return [part.strip() for part in raw.split(separator) if part.strip()]


def require_columns(fieldnames: List[str], required: List[str]) -> None:
    missing = [col for col in required if col not in fieldnames]
    if missing:
        raise ValueError(
            "Fehlende Pflichtspalten in der CSV: " + ", ".join(missing)
        )


def row_to_room(
    row: Dict[str, str],
    row_number: int,
    default_address: str,
    default_description: str,
    link_prefix: str,
) -> Dict[str, Any]:
    try:
        latitude = float((row.get("breitengrad") or "").replace(",", "."))
        longitude = float((row.get("laengengrad") or "").replace(",", "."))
    except ValueError as exc:
        raise ValueError(
            f"Ungültige Koordinaten in Zeile {row_number}: "
            f"breitengrad={row.get('breitengrad')!r}, "
            f"laengengrad={row.get('laengengrad')!r}"
        ) from exc

    room_id_raw = (row.get("id") or "").strip()
    room_id = int(room_id_raw) if room_id_raw else row_number

    title = (row.get("titel") or "").strip()
    if not title:
        raise ValueError(f"Leerer Titel in Zeile {row_number}")

    filename = (row.get("dateiname") or "").strip()
    if not filename:
        raise ValueError(f"Leerer Dateiname in Zeile {row_number}")

    address = (row.get("address") or default_address).strip()
    description = (row.get("description") or default_description).strip()


    links_value = row.get("links")
    if links_value is not None and links_value.strip():
        links = split_links(links_value)
    else:
        links = [f"{link_prefix}{filename}"] if filename else []

    return {
        "id": room_id,
        "title": title,
        "address": address,
        "description": description,
        "longitude": {
            "Lon": longitude,
        },
        "latitude": {
            "Lat": latitude,
        },
        "links": links,
    }


def read_rooms_from_csv(
    input_csv: Path,
    delimiter: str,
    encoding: str,
    default_address: str,
    default_description: str,
    link_prefix: str,
) -> List[Dict[str, Any]]:
    rooms: List[Dict[str, Any]] = []

    with input_csv.open("r", encoding=encoding, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("CSV enthält keine Kopfzeile")

        normalized = normalize_fieldnames(reader.fieldnames)
        reader.fieldnames = normalized
        require_columns(normalized, ["dateiname", "breitengrad", "laengengrad", "titel"])

        for index, row in enumerate(reader, start=1):
            # Leere Zeilen überspringen
            if not any((value or "").strip() for value in row.values()):
                continue
            room = row_to_room(
                row=row,
                row_number=index,
                default_address=default_address,
                default_description=default_description,
                link_prefix=link_prefix,
            )
            rooms.append(room)

    return rooms


def write_json(rooms: List[Dict[str, Any]], output_path: Path) -> None:
    payload = {"rooms": rooms}
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_xml(rooms: List[Dict[str, Any]], output_path: Path) -> None:
    root = Element("rooms")

    for room in rooms:
        room_el = SubElement(root, "room")

        SubElement(room_el, "id").text = str(room["id"])
        SubElement(room_el, "title").text = room["title"]
        SubElement(room_el, "address").text = room["address"]

        # CDATA für description via minidom nachträglich einfügen
        description_el = SubElement(room_el, "description")
        description_el.text = room["description"]

        longitude_el = SubElement(room_el, "longitude")
        SubElement(longitude_el, "Lon").text = str(room["longitude"]["Lon"])

        latitude_el = SubElement(room_el, "latitude")
        SubElement(latitude_el, "Lat").text = str(room["latitude"]["Lat"])

        links_el = SubElement(room_el, "links")
        for link in room["links"]:
            SubElement(links_el, "link").text = link

    rough_xml = tostring(root, encoding="utf-8")
    dom = minidom.parseString(rough_xml)

    # CDATA für description setzen
    for room_node, room in zip(dom.getElementsByTagName("room"), rooms):
        description_nodes = room_node.getElementsByTagName("description")
        if description_nodes:
            desc_node = description_nodes[0]
            while desc_node.firstChild:
                desc_node.removeChild(desc_node.firstChild)
            cdata = dom.createCDATASection(room["description"])
            desc_node.appendChild(cdata)

    pretty_xml = dom.toprettyxml(indent="  ", encoding="utf-8")
    with output_path.open("wb") as f:
        f.write(pretty_xml)


def main() -> int:
    args = parse_args()

    input_csv = Path(args.input_csv)
    xml_output = Path(args.xml_output)
    json_output = Path(args.json_output)

    if not input_csv.exists():
        print(f"Fehler: CSV-Datei nicht gefunden: {input_csv}", file=sys.stderr)
        return 1

    try:
        rooms = read_rooms_from_csv(
            input_csv=input_csv,
            delimiter=args.delimiter,
            encoding=args.encoding,
            default_address=args.default_address,
            default_description=args.default_description,
            link_prefix=args.link_prefix,
        )
        write_json(rooms, json_output)
        write_xml(rooms, xml_output)
    except Exception as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    print(f"JSON geschrieben: {json_output}")
    print(f"XML geschrieben:  {xml_output}")
    print(f"Anzahl Einträge:  {len(rooms)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
