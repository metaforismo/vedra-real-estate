FROM python:3.13-slim
ARG WITH_BROWSER=0
ARG WITH_CLOUD=0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
WORKDIR /app
COPY requirements.txt requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$WITH_CLOUD" = "1" ]; then pip install --no-cache-dir -r requirements-cloud.txt; fi \
    && if [ "$WITH_BROWSER" = "1" ]; then pip install --no-cache-dir playwright==1.57.0 && python -m playwright install --with-deps chromium; fi \
    && useradd --create-home --uid 10001 vedra \
    && mkdir -p /app/data && chown vedra:vedra /app/data
COPY --chown=vedra:vedra backend/app/ backend/app/
COPY --chown=vedra:vedra scripts/worker.py scripts/check_worker.py scripts/
COPY --chown=vedra:vedra frontend/ frontend/
USER vedra
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["python","-m","uvicorn","app.main:app","--app-dir","backend","--host","0.0.0.0","--port","8000","--workers","1","--no-proxy-headers"]
