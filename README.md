# File API

Minimaler Nginx-Container zum Ausliefern statischer API-Dateien wie XML und JSON.

Der Container stellt den Inhalt von `/api` read-only unter Port `8070` bereit. Damit koennen Dateien auf dem Host ausgetauscht werden, ohne das Image neu zu bauen.

## Features

- Leichtgewichtiges Image auf Basis von `nginx:alpine`
- Statische XML- und JSON-Dateien ueber HTTP
- `application/xml` als Standard-Content-Type
- Read-only Host-Volume fuer API-Dateien
- Hilfsskripte zum Erzeugen von GPS-CSV, `rooms.xml` und `rooms.json`

## Projektstruktur

```text
.
├── Dockerfile
├── docker-compose.yml
├── README.md
└── scrips/
    ├── csv_to_rooms_xml_json.py
    └── extract_gps_to_csv.py
```

## Starten

```bash
docker compose up -d --build
```

Die Dateien aus `/api` sind danach ueber `http://localhost:8070/` erreichbar.

Beispiele:

```bash
curl http://localhost:8070/wtg.xml
curl http://localhost:8070/wtg.json
```

## Host-Dateien

`docker-compose.yml` mountet den Host-Ordner `/api` nach `/usr/share/nginx/html`:

```yaml
volumes:
  - /api:/usr/share/nginx/html:ro
```

Lege die auszuliefernden Dateien deshalb auf dem Host unter `/api` ab, zum Beispiel:

```text
/api/wtg.xml
/api/wtg.json
```

Der Nginx-Index zeigt standardmaessig auf `wtg.xml`.

## Hilfsskripte

GPS-Daten aus Bildern in eine CSV schreiben:

```bash
python3 scrips/extract_gps_to_csv.py /pfad/zum/bilderordner -o scrips/gps_daten.csv
```

Ergaenze vor dem naechsten Schritt mindestens die Spalte `titel`, weil der Converter diese Pflichtspalte erwartet.

Aus einer CSV `rooms.xml` und `rooms.json` erzeugen:

```bash
python3 scrips/csv_to_rooms_xml_json.py scrips/gps_daten.csv \
  --xml-output /api/wtg.xml \
  --json-output /api/wtg.json
```

Die CSV muss mindestens diese Spalten enthalten:

```text
dateiname,breitengrad,laengengrad,titel
```

Optionale Spalten:

```text
id,address,description,links
```

## Git

Lokale Arbeitsdateien wie `gps_daten.csv`, `__pycache__/` und Dotfiles werden per `.gitignore` ignoriert.
