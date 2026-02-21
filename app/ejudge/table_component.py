import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiomysql
from aiomysql import Connection, Pool
from loguru import logger
from pydantic import BaseModel

from app.ejudge.config_parser import EjudgeConfigReader
from app.engine.config_loader import ConfigLoader
from app.storage.user_storage import UserStorage

UPDATE_PERIOD = 5


@dataclass
class SingleRow:
    run_id: int
    create_time: datetime
    last_change_time: datetime
    prob_id: int
    user_id: int
    status: int
    score: int
    test_num: int


class ProblemInfo(BaseModel):
    short: str
    long: str

    def serialize_for_public_api(self) -> dict:
        return {"short": self.short, "long": self.long}


class ContestInfo(BaseModel):
    contest_id: int
    task_number: int
    name: str
    problems: list[ProblemInfo]
    is_acm: bool

    def serialize_for_public_api(self) -> dict:
        return {
            "contest_id": self.contest_id,
            "task_number": self.task_number,
            "name": self.name,
            "problems": [
                problem.serialize_for_public_api() for problem in self.problems
            ],
            "is_acm": self.is_acm,
        }


class SingleProblemResult(BaseModel):
    bad_submissions: list[datetime] = []
    ok_submission: datetime = datetime.max
    score_time: dict[int, datetime] = {}

    def get_result(self, is_acm: bool, deadline: datetime) -> int:
        if is_acm:
            bad_attempts = sum(sub < deadline for sub in self.bad_submissions)
            if self.ok_submission < deadline:
                return bad_attempts + 1
            return -bad_attempts
        else:
            result = -1
            for key, value in self.score_time.items():
                if value < deadline:
                    result = max(result, key)
            return result


class ContestCache:
    def __init__(self, header: ContestInfo):
        self.header: ContestInfo = header
        self.users: dict[str, list[SingleProblemResult]] = dict()
        self.last_change_time: datetime = datetime.min

    def push(self, login: str, row: SingleRow):
        if login not in self.users:
            user_result = [
                SingleProblemResult() for _ in range(self.header.task_number)
            ]
            self.users[login] = user_result
        else:
            user_result = self.users[login]

        if not (1 <= row.prob_id <= len(user_result)):
            logger.warning(
                f"Unexpected problem_id: {row.prob_id} in contest {self.header.contest_id}"
            )
            return

        prob_result = user_result[row.prob_id - 1]

        if self.header.is_acm:
            if row.status == 0:  # OK
                if row.create_time < prob_result.ok_submission:
                    prob_result.ok_submission = row.create_time
                    prob_result.bad_submissions = [
                        bad
                        for bad in prob_result.bad_submissions
                        if bad < row.create_time
                    ]
            elif row.test_num != 0 and row.status in [
                1,  # CE
                2,  # RT
                3,  # TL
                4,  # PE
                5,  # WA
                # 6,  # CF
                7,  # PT
                # 9,  # IG
                10,  # DQ
                # 11,  # PD
                12,  # ML
                13,  # SE
                14,  # SV
                15,  # WT
                17,  # RJ
            ]:
                if row.create_time < prob_result.ok_submission:
                    prob_result.bad_submissions.append(row.create_time)
        else:
            score = row.score if row.status in [0, 7] else 0
            if prob_result.score_time.get(score, datetime.max) > row.create_time:
                prob_result.score_time[score] = row.create_time


class TableComponent:
    def __init__(self, user_storage: UserStorage, config_loader: ConfigLoader):
        self._config_loader = config_loader
        self._user_storage = user_storage
        self._ejudge_config_reader = EjudgeConfigReader(Path("/home/judges"))

        self.cache: dict[int, ContestCache] = dict()

    async def run_update_loop(self, pool: Pool):
        while True:
            try:
                start = time.time()
                async with pool.acquire() as conn:
                    await self._update(conn)
                end = time.time()
                logger.info(f"Update took {end - start:.2f} seconds")
            except Exception as err:
                logger.error(f"Exception while updating table: {err}")
                logger.exception(err)
            finally:
                await asyncio.sleep(UPDATE_PERIOD)

    def get_info(self, contest_id: int) -> Optional[ContestInfo]:
        config = self._ejudge_config_reader.read_config(contest_id)
        if config is None:
            return None

        count = len(config.dirs["problem"])
        score_system = config.dirs[""][0].args.get("score_system", "")
        if score_system not in ["kirov", "acm"]:
            logger.warning(
                f"Unexpected score system for contest {contest_id}: {score_system}"
            )
            return None

        problems = []
        for pos, item in enumerate(config.dirs["problem"]):
            short = item.args.get("short_name", chr(ord("A") + pos))
            long = item.args.get("long_name", "")
            problems.append(ProblemInfo(short=short, long=long))

        return ContestInfo(
            task_number=count,
            name=config.pretty_name,
            problems=problems,
            contest_id=contest_id,
            is_acm=(score_system == "acm"),
        )

    async def _update(self, connection: Connection):
        config = self._config_loader.get_config()

        all_contests: set[int] = set()
        for course in config.course_config.values():
            for lesson in course.lessons:
                all_contests.add(lesson.contest.id)
            for standing in course.standings.values():
                for contest in standing.contests:
                    all_contests.add(contest)

        logger.info(f"Found {len(all_contests)} contests")

        for item in set(self.cache.keys()):
            if item not in all_contests:
                self.cache.pop(item)

        for contest_id in all_contests:
            bad_cnt = 0
            good_cnt = 0

            header = self.get_info(contest_id)
            if header is None:
                self.cache.pop(contest_id, None)
                continue

            if contest_id not in self.cache or self.cache[contest_id].header != header:
                self.cache[contest_id] = ContestCache(header)
                logger.info(f"Reset table '{contest_id}'")

            table_cache = self.cache[contest_id]

            async for row in self._single_contest_update(
                connection, contest_id, table_cache.last_change_time
            ):
                table_cache.last_change_time = max(
                    table_cache.last_change_time, row.last_change_time
                )
                if row.user_id not in self._user_storage.login_by_user_id:
                    bad_cnt += 1
                else:
                    login = self._user_storage.login_by_user_id[row.user_id]
                    table_cache.push(login, row)
                    good_cnt += 1

            if bad_cnt != 0 or good_cnt != 0:
                total = good_cnt + bad_cnt
                logger.info(
                    f"{contest_id}: Total bad rows: {bad_cnt} ({bad_cnt / total :.2%}), "
                    f"good rows: {good_cnt} ({good_cnt / total :.2%})"
                )

    async def _single_contest_update(
        self, connection: Connection, contest_id: int, start_time: datetime
    ):
        async with connection.cursor(aiomysql.SSCursor) as cur:
            query = """
            SELECT run_id, create_time, last_change_time, prob_id, user_id, status, score, test_num
            FROM runs
            WHERE last_change_time > %s and contest_id = %s
            ORDER BY last_change_time
            """
            await cur.execute(
                query,
                (start_time, contest_id),
            )
            async for (
                run_id,
                create_time,
                last_change_time,
                prob_id,
                user_id,
                status,
                score,
                test_num,
            ) in cur:
                yield SingleRow(
                    run_id=run_id,
                    create_time=create_time,
                    last_change_time=last_change_time,
                    prob_id=prob_id,
                    user_id=user_id,
                    status=status,
                    score=score,
                    test_num=test_num,
                )

    def get_user_score(self, login: str, contests: list[tuple[int, datetime]]) -> dict:
        per_contest = []
        sum_score = 0

        for contest_id, deadline in contests:
            if contest_id not in self.cache:
                continue
            contest_cache: ContestCache = self.cache[contest_id]

            if login not in contest_cache.users:
                per_contest.append({"score": 0, "tasks": None})
                continue

            tasks = []
            upsolving = []
            contest_score = 0

            for item in contest_cache.users[login]:
                result = item.get_result(contest_cache.header.is_acm, deadline)
                upsolved = item.get_result(contest_cache.header.is_acm, datetime.max)

                tasks.append(result)
                upsolving.append(upsolved)

                if contest_cache.header.is_acm:
                    contest_score += result > 0
                else:
                    contest_score += max(result, 0)
            per_contest.append(
                {"tasks": tasks, "upsolving": upsolving, "score": contest_score}
            )
            sum_score += contest_score

        return {"per_contests": per_contest, "score": sum_score}
