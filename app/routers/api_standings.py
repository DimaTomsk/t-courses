from datetime import datetime

from fastapi import APIRouter
from starlette.responses import JSONResponse

from app.ejudge.table_component import (
    TableComponent,
    ContestInfo,
)
from app.engine.config_loader import ConfigLoader
from app.models.config import Course
from app.storage.user_storage import UserStorage


class ApiStandings:
    def __init__(
        self,
        user_storage: UserStorage,
        config_loader: ConfigLoader,
        table_component: TableComponent,
    ):
        self._router = APIRouter(prefix="/standings", tags=["standings"])

        self._table_component: TableComponent = table_component
        self._config_loader = config_loader
        self._user_storage = user_storage

        self._router.add_api_route(
            "/{course_name}/{table_name}",
            self.standings,
            methods=["GET"],
            name="standings.table",
        )

    def get_router(self):
        return self._router

    async def standings(self, course_name: str, table_name: str):
        config = self._config_loader.get_config()

        if course_name not in config.course_config:
            return JSONResponse(
                status_code=404, content={"message": "Course not found"}
            )
        course: Course = config.course_config[course_name]
        table = course.get_contests_for_table(table_name)
        if table is None:
            return JSONResponse(
                status_code=404, content={"message": "Standings not found"}
            )

        good_contests = [
            contest_id
            for contest_id in table.contests
            if contest_id in self._table_component.cache
        ]
        headers: list[ContestInfo] = []

        all_users: set[str] = set()

        for contest_id in good_contests:
            cache = self._table_component.cache[contest_id]
            headers.append(cache.header.serialize_for_public_api())
            all_users |= cache.users.keys()

        deadlines: dict[int, datetime] = {}
        for lesson in course.lessons:
            contest = lesson.contest
            deadlines[contest.id] = contest.deadline.absolute

        standings = []
        for login in all_users:
            user = self._user_storage.get_user_by_login(login)
            if user is None:
                continue
            with_deadlines = [
                (contest_id, deadlines.get(contest_id, datetime.max))
                for contest_id in good_contests
            ]
            data = self._table_component.get_user_score(login, with_deadlines)
            data["name"] = f"{user.get_field('surname')} {user.get_field('name')}"
            standings.append(data)

        standings.sort(key=lambda x: (-x["score"], x["name"]))
        i = 0
        while i < len(standings):
            j = i
            while j < len(standings) and standings[i]["score"] == standings[j]["score"]:
                j += 1
            if i + 1 == j:
                standings[i]["place"] = f"{i + 1}"
            else:
                for x in range(i, j):
                    standings[x]["place"] = f"{i + 1}-{j}"
            i = j

        response = {
            "contests": headers,
            "standings": standings,
        }

        return JSONResponse(
            status_code=200,
            content=response,
            media_type="application/json; charset=utf-8",
        )
