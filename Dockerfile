FROM nginx:alpine

# XML-Dateien in das Web-Verzeichnis kopieren
COPY data/ /usr/share/nginx/html/

# Explizit Content-Type für XML setzen
RUN printf "server {\n\
    listen 80;\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        default_type application/xml;\n\
        index example.xml;\n\
    }\n\
}\n" > /etc/nginx/conf.d/default.conf

EXPOSE 80
