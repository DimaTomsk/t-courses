import json
import shutil
import tempfile
from pathlib import Path

from git import Repo
from loguru import logger

from app.forms.form import Form
from app.models.config import GlobalConfig, Course, Page

CONFIGS_PATH = Path("configs")

REPO_NAME = "t-edu-config"
MAIN_BRANCH = "main"
REPO_FULL_PATH = f"git@github.com:DimaTomsk/{REPO_NAME}.git"


class ConfigLoader:
    def __init__(self) -> None:
        assert CONFIGS_PATH.exists()
        self.config_path: Path = CONFIGS_PATH / REPO_NAME
        if not self.config_path.exists():
            self.update()

    def update(self):
        logger.info("Updating configs...")
        with tempfile.TemporaryDirectory() as backup_dir:
            if self.config_path.exists():
                logger.info("Copy to temp dir...")
                shutil.copytree(self.config_path, backup_dir, dirs_exist_ok=True)

            logger.info(f"Loading config from '{REPO_FULL_PATH}'")
            try:
                if self.config_path.exists():
                    repo = Repo(self.config_path)
                    origin = repo.remote()
                    origin.fetch()
                    repo.git.reset("--hard", f"origin/{repo.active_branch.name}")
                else:
                    Repo.clone_from(REPO_FULL_PATH, self.config_path)

                logger.info("Testing config...")
                self.get_config()
                logger.success(
                    f"Config loaded from '{REPO_FULL_PATH}' to '{self.config_path}'"
                )
            except Exception as e:
                logger.warning("Bad configs :( rollback...")
                shutil.rmtree(self.config_path)
                shutil.copytree(backup_dir, self.config_path, dirs_exist_ok=True)
                raise e

    @staticmethod
    def read_json(path: Path):
        with open(path, "rt", encoding="utf-8") as f:
            return json.load(f)

    def get_config(self) -> GlobalConfig:
        pages: dict[str, Page] = {}
        for item in (self.config_path / "pages").glob("*.json"):
            pages[item.stem] = Page.model_validate(json.loads(item.read_text()))

        courses: dict[str, Course] = {}
        for item in (self.config_path / "courses").glob("*.json"):
            courses[item.stem] = Course.model_validate(json.loads(item.read_text()))

        forms: dict[str, Form] = {}
        forms_path = self.config_path / "forms"
        for item in forms_path.rglob("*.json"):
            name = str(item.relative_to(forms_path).with_suffix(""))
            forms[name] = Form.model_validate(self.read_json(item))

        return GlobalConfig(pages, courses, forms)
