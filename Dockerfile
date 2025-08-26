FROM python:3.10

COPY --from=ghcr.io/astral-sh/uv:0.7.21 /uv /uvx /bin/

ADD . /app

WORKDIR /app

RUN uv sync --locked

EXPOSE 8000

CMD [ "uv", "run", "fastapi", "dev", "main.py", "--host", "0.0.0.0", "--port", "8000"]