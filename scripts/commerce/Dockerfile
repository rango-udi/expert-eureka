FROM python:3.12-slim-bookworm AS tools
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/fuzcake-data
WORKDIR /workspace
RUN pip install --no-cache-dir requests==2.32.5 openpyxl==3.1.5
COPY commands.py /opt/commerce/commands.py
ENTRYPOINT ["python", "/opt/commerce/commands.py"]

FROM tools AS robot
# Browser Batteries Node links libatomic even when Chromium dependencies are present.
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN pip install --no-cache-dir robotframework==7.3.2 robotframework-browser==19.10.0 \
    && python -m Browser.entry install --with-deps chromium
ENTRYPOINT ["robot", "--outputdir", "/workspace/reports", "/checks/store.robot"]
