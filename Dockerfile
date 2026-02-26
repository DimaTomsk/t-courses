FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install git -y

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ app/
COPY resources/ resources/
COPY secrets/production.env secrets/.env

# Setup environment for config update (from github):
COPY secrets/private_config_key /root/.ssh/id_ed25519
# Source: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
COPY secrets/github_known_hosts /root/.ssh/known_hosts
RUN chmod 0600 /root/.ssh/id_ed25519

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN date > /etc/build-info

ENTRYPOINT ["docker-entrypoint.sh"]

CMD [ "/usr/local/bin/uvicorn", "--host", "127.0.0.1", "--port", "8084", "--workers", "1", "app.main:app" ]
