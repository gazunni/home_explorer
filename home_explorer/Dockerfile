FROM python:3.12-alpine
LABEL io.hass.version="0.1.0" io.hass.type="app" io.hass.arch="aarch64"
WORKDIR /opt/home-explorer
COPY server.py ./server.py
COPY web ./web
RUN addgroup -S explorer && adduser -S -G explorer explorer
USER explorer
EXPOSE 8099
CMD ["python", "-B", "server.py"]
