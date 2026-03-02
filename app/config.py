from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tandoor_url: str = ""
    tandoor_token: str = ""
    log_level: str = "INFO"
    profiles_dir: str = "data/profiles"
    data_dir: str = "data"
    log_to_stdout: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
