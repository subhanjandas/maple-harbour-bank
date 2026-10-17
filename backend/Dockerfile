FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock /tmp/deps/
RUN pip install --no-cache-dir uv==0.12.23 && cd /tmp/deps && uv export --frozen --no-dev --no-emit-project -o requirements.txt && pip install --no-cache-dir -r requirements.txt
COPY backend/mhb /app/mhb
COPY db /db
COPY architecture /architecture
COPY scripts /scripts
# Config file paths resolve through /app/mhb -> /; use matching root for packaged assets.
RUN useradd --uid 10001 --create-home app
USER app
EXPOSE 8000
CMD ["uvicorn","mhb.asgi:app","--host","0.0.0.0","--port","8000","--no-access-log"]
