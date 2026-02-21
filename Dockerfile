FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install git -y

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ app/
COPY resources/ resources/
COPY secrets/ secrets/

ENTRYPOINT [ "/usr/local/bin/uvicorn", "--host", "127.0.0.1", "--port", "8084", "--workers", "1", "app.main:app" ]
