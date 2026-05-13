FROM nginx:alpine

RUN apk add --no-cache openssl \
    && mkdir -p /etc/nginx/ssl \
    && openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/selfsigned.key \
        -out /etc/nginx/ssl/selfsigned.crt \
        -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,DNS:api-server,IP:127.0.0.1" \
    && chmod 600 /etc/nginx/ssl/selfsigned.key

# XML-Dateien in das Web-Verzeichnis kopieren
#COPY data/ /usr/share/nginx/html/

# Explizit Content-Type fuer XML setzen
RUN printf "server {\n\
    listen 80;\n\
    listen 443 ssl;\n\
\n\
    ssl_certificate /etc/nginx/ssl/selfsigned.crt;\n\
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;\n\
    ssl_protocols TLSv1.2 TLSv1.3;\n\
    ssl_ciphers HIGH:!aNULL:!MD5;\n\
\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        default_type application/xml;\n\
        index wtg.xml;\n\
    }\n\
}\n" > /etc/nginx/conf.d/default.conf

EXPOSE 80 443
