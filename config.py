from pathlib import Path
from typing import List, Union

from nonebot import get_driver
from pydantic import Extra, BaseModel, validator

from .apikey import APIKeyPool
from nonebot import get_plugin_config


class Config(BaseModel, extra=Extra.ignore, arbitrary_types_allowed=True):
    api_key: Union["APIKeyPool", str, List[str]] = None
    key_load_balancing: bool = False
    history_save_path: Path = Path("data/ChatHistory").absolute()
    preset_path: Path = Path("data/Presets").absolute()
    openai_proxy: str = None
    openai_api_base: str = "https://api.openai.com/v1"
    chat_memory_max: int = 10
    history_max: int = 100
    temperature: float = 0.5
    model_name: str = 'gpt-3.5-turbo'
    allow_private: bool = True
    change_chat_to: str = None
    max_tokens: int = 1024
    auto_create_preset_info: bool = True
    customize_prefix: str = '/'
    customize_talk_cmd: str = 'talk'
    timeout: int = 10
    default_only_admin: bool = False
    at_sender: bool = True

    @validator('api_key')
    def api_key_validator(cls, v) -> APIKeyPool:
        return APIKeyPool(v)


plugin_config = get_plugin_config(Config)
