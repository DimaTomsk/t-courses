from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel

from app.forms.form import Form


class StrictModel(BaseModel, extra="forbid", strict=True):
    pass


class Teacher(StrictModel):
    name: str
    img: str
    tg: str


class Link(StrictModel):
    name: str
    url: str


class Deadline(BaseModel):
    absolute: datetime = datetime.max
    rel_course_join: Optional[timedelta] = None
    rel_contest_start: Optional[timedelta] = None


class Contest(BaseModel):
    name: str
    id: int
    tag: str
    show_standings: bool = False
    deadline: Deadline = Deadline()


class Recordings(StrictModel):
    youtube: Optional[str] = None
    vkvideo: Optional[str] = None


class Lesson(StrictModel):
    date: str
    title: str
    contest: Contest
    attachments: Optional[list[Link]] = None
    recordings: Optional[Recordings] = None


class JoinButton(StrictModel):
    name: str
    tag: str


class TableConfig(BaseModel):
    contests: list[int]


class Course(BaseModel):
    title: str

    teachers: list[Teacher]
    links: list[Link]
    lessons: list[Lesson]
    join_buttons: list[JoinButton]
    standings: dict[str, TableConfig] = {}

    def get_contests_for_table(self, table_name: str) -> Optional[TableConfig]:
        if table_name in self.standings:
            return self.standings[table_name]
        for lesson in self.lessons:
            contest = lesson.contest
            if str(contest.id) == table_name and contest.show_standings:
                return TableConfig(contests=[contest.id])
        return None

    def get_contest_by_tag(self, tag: str) -> set[int]:
        result = set()
        for lesson in self.lessons:
            if tag == lesson.contest.tag:
                result.add(lesson.contest.id)
        return result

    def get_contests_by_tags(self, tags: list[str]) -> set[int]:
        result = set()
        for tag in tags:
            result |= self.get_contest_by_tag(tag)
        return result


class PageItem(BaseModel):
    link: str
    title: str
    description: str
    hint: str = ""


class Page(BaseModel):
    title: str
    items: list[PageItem]
    links: list[Link]


@dataclass
class GlobalConfig:
    pages: dict[str, Page]
    course_config: dict[str, Course]
    forms_config: dict[str, Form]
