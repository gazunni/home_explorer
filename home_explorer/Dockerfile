FROM python:3.12-alpine
LABEL io.hass.version="0.33.0" io.hass.type="app" io.hass.arch="aarch64|amd64"
WORKDIR /opt/home-explorer
RUN pip install --no-cache-dir "websockets==15.0.1" && addgroup -S explorer && adduser -S -s /bin/sh -G explorer explorer
COPY server.py ./server.py
COPY entrypoint.sh ./entrypoint.sh
COPY web ./web
RUN mkdir -p /data && chmod 0755 ./entrypoint.sh && chown -R explorer:explorer /opt/home-explorer
EXPOSE 8099
CMD ["/opt/home-explorer/entrypoint.sh"]
