import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SubConfig:
    flags: list[str]
    args: dict[str, str]


@dataclass
class ContestConfig:
    name: str
    dirs: dict[str, list[SubConfig]]

    def push_to_section(self, section: str) -> SubConfig:
        if section not in self.dirs:
            self.dirs[section] = []
        subconfig = SubConfig([], {})
        self.dirs[section].append(subconfig)
        return subconfig


def remove_quotes(s: str) -> str:
    s = s.strip()
    if len(s) > 0 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


class EjudgeConfigReader:
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def read_config(self, contest_id: int) -> Optional[ContestConfig]:
        cfg_file = self.config_path / f"{contest_id:06}/conf/serve.cfg"
        xml_config = self.config_path / f"data/contests/{contest_id:06}.xml"
        if not cfg_file.exists() or not xml_config.exists():
            return None

        tree = ET.parse(xml_config)
        root = tree.getroot()
        name = root.find("name").text
        result = ContestConfig(name, {})

        with open(cfg_file, "rt", encoding="utf-8") as cfg_file_read:
            current_section = result.push_to_section("")
            for line in cfg_file_read:
                line = line.strip()
                if len(line) == 0 or line[0] == "#":
                    continue
                if line[0] == "[" and line[-1] == "]":
                    current_section = result.push_to_section(line[1:-1])
                    continue

                if "=" in line:
                    name, value = line.split("=", maxsplit=1)
                    current_section.args[remove_quotes(name)] = remove_quotes(value)
                else:
                    current_section.flags.append(line)

        return result
