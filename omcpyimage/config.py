from pydantic import BaseModel


class Config(BaseModel):
    omc: list[str]
    py: list[str]
