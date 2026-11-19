# Legacy application runtime is isolated from the modern Robot browser runtime.
FROM python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f AS app
# Mark the container-only maintenance environment.
ENV CMDC_CONTAINER=1
# Keep bytecode out of source bind mounts.
ENV PYTHONDONTWRITEBYTECODE=1
# Flush command status immediately.
ENV PYTHONUNBUFFERED=1
# Avoid package download caches in image layers.
ENV PIP_NO_CACHE_DIR=1
# BuildKit owns progress; suppress duplicate package bars.
ENV PIP_PROGRESS_BAR=off
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libxml2-dev libxslt1-dev zlib1g-dev libjpeg-dev \
    libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt constraints.txt ./
COPY config/source-lock.json config/source-lock.json
COPY scripts/prepare_upstream.py scripts/prepare_upstream.py
RUN python -m pip install --disable-pip-version-check pip==24.0 setuptools==68.2.2 wheel==0.41.3 \
    && python scripts/prepare_upstream.py /tmp/upstream \
    && python -m pip install -c constraints.txt -r requirements.txt /tmp/upstream/shuup-3.1.0-py2.py3-none-any.whl \
    && python -m pip check \
    && rm -rf /tmp/upstream
COPY --from=fuzcake-data /records /fuzcake-data/records
COPY --from=fuzcake-data /assets /fuzcake-data/assets
COPY --from=fuzcake-data /fuzcake_data /fuzcake-data/fuzcake_data
COPY --from=fuzcake-data /LICENSE.txt /fuzcake-data/LICENSE.txt
COPY --from=fuzcake-data /attribution.json /fuzcake-data/attribution.json
COPY --from=test-design / /test-design
# Shared test design has no application imports.
ENV PYTHONPATH=/test-design
COPY . .
CMD ["python", "scripts/web_server.py"]

FROM python:3.12-slim-bookworm AS robot
# Browser Batteries Node links libatomic even when Chromium dependencies are present.
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*
# Restrict this image to browser commands through the shared container CLI.
ENV CMDC_CONTAINER=1
# Flush Robot and launcher output immediately.
ENV PYTHONUNBUFFERED=1
# Avoid bytecode in bind-mounted source.
ENV PYTHONDONTWRITEBYTECODE=1
# Keep browser binaries in the image directory used by the runtime helper.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY requirements-robot.txt ./
RUN python -m pip install --no-cache-dir -r requirements-robot.txt \
    && python -m Browser.entry install --with-deps chromium \
    && python -c "import subprocess; from importlib.metadata import distribution; subprocess.run([str(distribution('robotframework-browser-batteries').locate_file('BrowserBatteries/bin/node')), '--version'], check=True)"
COPY --from=fuzcake-data /records /fuzcake-data/records
COPY --from=fuzcake-data /assets /fuzcake-data/assets
COPY --from=fuzcake-data /fuzcake_data /fuzcake-data/fuzcake_data
COPY --from=fuzcake-data /LICENSE.txt /fuzcake-data/LICENSE.txt
COPY --from=fuzcake-data /attribution.json /fuzcake-data/attribution.json
COPY --from=test-design / /test-design
# Shared test design has no application imports.
ENV PYTHONPATH=/test-design
COPY . .
CMD ["python", "scripts/commands.py", "robot"]

# Documentation export stays separate from both legacy Django and Browser.
FROM python:3.12-slim-bookworm AS report
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /app
COPY requirements-report.txt ./
RUN python -m pip install --no-cache-dir -r requirements-report.txt
COPY --from=test-design / /test-design
ENV PYTHONPATH=/test-design
COPY scripts/ scripts/
CMD ["python", "scripts/customer_report.py"]
