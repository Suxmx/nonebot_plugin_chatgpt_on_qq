from typing import Optional
from pathlib import Path
from pydantic import Extra, BaseModel


class Config(BaseModel, extra=Extra.ignore):
    api_key: str = "NoKey"
    history_save_path: Path = Path("data/ChatHistory").absolute()
    preset_path: Path = Path("data/Presets").absolute()
    openai_proxy: str = None
    openai_api_base: str = None
    history_max: int = 10
    openai_api_base:str=None
