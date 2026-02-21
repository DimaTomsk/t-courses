from dataclasses import dataclass
from typing import Optional

import aiohttp

from app.ejudge.registration import COMMON_EJUDGE_PASSWORD


@dataclass
class LoginResult:
    SID: str
    EJSID: str


async def perform_login(contest_id: str, login: str) -> Optional[LoginResult]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://ej-3.t-edu.tech/cgi-bin/new-client",
                data={
                    "contest_id": contest_id,
                    "role": "0",
                    "prob_name": "",
                    "login": login,
                    "password": COMMON_EJUDGE_PASSWORD,
                    "locale_id": 1,
                    "action_2": "Войти",
                },
            ) as response:
                return LoginResult(
                    SID=response.url.query["SID"],
                    EJSID=response.cookies.get("EJSID").value,
                )
    except Exception as error:
        return None
