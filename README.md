# XML Server (Docker + Nginx)

Minimaler Docker-Container zum Ausliefern von XML-Dateien über HTTP.

## Features

- Leichtgewichtiges Image auf Basis von `nginx:alpine`
- Korrekte XML-Auslieferung mit `Content-Type: application/xml`
- Kein zusätzlicher Applikationscode notwendig
- Geeignet für Feeds, Webhooks, Tests und einfache API-Antworten

## Projektstruktur

```text
.
├── Dockerfile
├── data/
│   └── example.xml
└── docker-compose.portainer.yml
```

## Schnellstart

```bash
docker build -t xml-server .
docker run -d -p 8080:80 --name xml-server xml-server
curl http://localhost:8080/example.xml
```

## Einsatz mit Portainer

Für dynamisches Ersetzen der XML-Dateien kann in Portainer ein Read-Only-Volume auf `/usr/share/nginx/html` gemountet werden (siehe `docker-compose.portainer.yml`).
