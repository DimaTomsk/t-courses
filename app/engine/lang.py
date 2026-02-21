import secrets

translit_dict = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sh",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    " ": "_",
    "ë": "e",
    "қ": "k",
    "і": "i",
}


def translit_single(x: str) -> str:
    if "a" <= x <= "z" or x == "-":
        return x
    return translit_dict.get(x, "")


def translit(s: str) -> str:
    return "".join(translit_single(ch) for ch in s.lower().strip())


class LoginGenerator:
    def __init__(self, surname: str, *, version: int = 0, prefix="t-gen"):
        self.surname = translit(surname.lower())
        self.version = version
        self.prefix = prefix

    def next(self):
        return LoginGenerator(
            self.surname, version=self.version + 1, prefix=self.prefix
        )

    def __str__(self):
        if self.version == 0:
            return f"{self.prefix}-{self.surname}"
        return f"{self.prefix}-{self.surname}-{self.version}"

    @classmethod
    def gen_password(cls) -> str:
        return (
            secrets.token_urlsafe(10)
            .lower()
            .replace("0", "r")
            .replace("o", "x")
            .replace("_", "u")
            .replace("-", "d")
            .replace("1", "p")
            .replace("l", "k")
        )
