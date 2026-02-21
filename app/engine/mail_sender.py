import json
import os

import aiohttp
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from loguru import logger

EMAIL_ACCESS_KEY = os.environ["EMAIL_ACCESS_KEY"]
EMAIL_SECRET_KEY = os.environ["EMAIL_SECRET_KEY"]


async def send_email(to_address: str, login: str, password: str):
    logger.info("Sending email...)")

    data = {
        "FromEmailAddress": "info@t-edu.tech",
        "Destination": {"ToAddresses": [to_address]},
        "Content": {
            "Simple": {
                "Subject": {"Data": "Логин для входа"},
                "Body": {
                    "Text": {
                        "Data": "Привет! Данные для входа в https://algocourses.ru\n"
                        f"Логин: {login}\n"
                        f"Пароль: {password}\n"
                    }
                },
            }
        },
    }
    creds = Credentials(EMAIL_ACCESS_KEY, EMAIL_SECRET_KEY)

    try:
        request = AWSRequest(
            method="POST",
            url="https://postbox.cloud.yandex.net/v2/email/outbound-emails",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        SigV4Auth(creds, "ses", "ru-central1").add_auth(request)

        async with aiohttp.ClientSession() as s:
            async with s.post(
                request.url, data=request.body, headers=dict(request.headers)
            ) as r:
                logger.info(await r.text())
    except Exception as e:
        pass
