FROM python:3.12-alpine
LABEL io.hass.version="0.3.0" io.hass.type="app" io.hass.arch="aarch64"
WORKDIR /opt/home-explorer
RUN pip install --no-cache-dir "websockets==15.0.1" && addgroup -S explorer && adduser -S -G explorer explorer
COPY server.py ./server.py
COPY web ./web
RUN mkdir -p /data
COPY entrypoint.sh ./entrypoint.sh
RUN chmod 755 ./entrypoint.sh
EXPOSE 8099
CMD ["./entrypoint.sh"]
