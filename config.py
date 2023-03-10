from typing import Optional
from pathlib import Path
from pydantic import Extra, BaseModel


class Config(BaseModel, extra=Extra.ignore):
    api_key:str="NoKey"
    history_save_path:Path=Path("data/ChatHistory").absolute()
    openai_proxy:str=None