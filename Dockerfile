FROM python:3.13-slim AS builder
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV VIRTUAL_ENV=/opt/venv

RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --upgrade pip setuptools wheel
RUN pip install .

FROM python:3.13-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV APP_PORT=3000

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
COPY app ./app
COPY pyproject.toml README.md ./

EXPOSE 3000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
