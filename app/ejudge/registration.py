import os

from aiomysql import Pool

EJUDGE_USER = os.environ["EJUDGE_USER"]
EJUDGE_PASSWORD = os.environ["EJUDGE_PASSWORD"]

COMMON_EJUDGE_PASSWORD = os.environ["COMMON_EJUDGE_PASSWORD"]
CONTEST_ID = 999999


async def create_new_user(login: str, name: str, pool: Pool) -> int:
    async with pool.acquire() as connection:
        cursor = await connection.cursor()
        try:
            await cursor.execute(
                "INSERT INTO logins (login, pwdmethod, password) VALUES (%s, %s, %s)",
                (login, 0, COMMON_EJUDGE_PASSWORD),
            )
            await connection.commit()
        except Exception as e:
            pass

        await cursor.execute("SELECT user_id FROM logins WHERE login = %s", (login,))
        user_id = (await cursor.fetchone())[0]

        try:
            await cursor.execute(
                "INSERT INTO cntsregs (user_id, contest_id) VALUES (%s, %s)",
                (user_id, CONTEST_ID),
            )
            await connection.commit()
        except Exception as err:
            pass

        try:
            await cursor.execute(
                "INSERT INTO users (user_id, contest_id, username) VALUES (%s, %s, %s)",
                (user_id, CONTEST_ID, name),
            )
            await connection.commit()
        except Exception as err:
            pass

    return user_id
