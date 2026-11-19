# Fetch and verify source separately from the runtime image.
FROM python:3.12-slim-bookworm AS source
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY config/source-lock.json /source-lock.json
COPY scripts/prepare_upstream.py /prepare_upstream.py
RUN python /prepare_upstream.py /opt/wowy

FROM python:3.12-slim-bookworm AS app
# All maintenance and application execution belongs to this container.
ENV CMDC_CONTAINER=1
# Keep bytecode out of source and shared data mounts.
ENV PYTHONDONTWRITEBYTECODE=1
# Flush process messages immediately.
ENV PYTHONUNBUFFERED=1
# Avoid package caches in layers.
ENV PIP_NO_CACHE_DIR=1
# Leave progress rendering to BuildKit.
ENV PIP_PROGRESS_BAR=off
# Local adapter, upstream modules and shared records have distinct roots.
ENV PYTHONPATH=/app:/opt/wowy:/fuzcake-data
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --disable-pip-version-check -r requirements.txt \
    && python -m pip check
COPY --from=source /opt/wowy /opt/wowy
COPY overrides/ /opt/wowy/
COPY --from=fuzcake-data /records /fuzcake-data/records
COPY --from=fuzcake-data /assets /fuzcake-data/assets
COPY --from=fuzcake-data /fuzcake_data /fuzcake-data/fuzcake_data
COPY --from=fuzcake-data /LICENSE.txt /fuzcake-data/LICENSE.txt
COPY --from=fuzcake-data /attribution.json /fuzcake-data/attribution.json
COPY . .
CMD ["python", "scripts/web_server.py"]

FROM app AS robot
# Browser Batteries Node links libatomic even when Chromium dependencies are present.
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*
# Chromium is installed once in the optional browser target.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY requirements-robot.txt ./
RUN python -m pip install --disable-pip-version-check -r requirements-robot.txt \
    && python -m Browser.entry install --with-deps chromium \
    && python -c "import subprocess; from importlib.metadata import distribution; subprocess.run([str(distribution('robotframework-browser-batteries').locate_file('BrowserBatteries/bin/node')), '--version'], check=True)"
CMD ["python", "scripts/commands.py", "robot"]
