from typing import Optional

from app.engine.config_loader import ConfigLoader
from app.models.config import Contest


class CourseRenderer:
    def __init__(self, config_loader: ConfigLoader):
        self.files_path = config_loader.config_path / "files"
        assert self.files_path.is_dir(), "Files path must be a directory"

    def statement_path(self, course: str, contest: Contest):
        path = self.files_path / course / f"{contest.id}.pdf"
        if path.exists() and path.is_file():
            return f"{course}/{contest.id}.pdf"
        return None

    @classmethod
    def parse_vk_params(cls, vk_url: str) -> Optional[dict]:
        if not "vkvideo.ru" in vk_url:
            return None
        split = vk_url.split("video.ru/video")
        if len(split) != 2:
            return None
        split = split[1].split("_")
        if len(split) != 2:
            return None
        return {"oid": split[0], "id": split[1]}

    @classmethod
    def parse_yt_params(cls, yt_url: str) -> Optional[dict]:
        if not "youtu.be" in yt_url:
            return None
        split = yt_url.split("tu.be/")
        if len(split) != 2:
            return None
        return {"id": split[1]}
