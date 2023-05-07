from pathlib import Path
from typing import List, Union

from nonebot import get_driver
from pydantic import Extra, BaseModel, validator

from .custom_errors import ApiKeyError, NoApiKeyError


class Config(BaseModel, extra=Extra.ignore):
    api_key: Union[str, List[str]] = None
    key_load_balancing: bool = False
    history_save_path: Path = Path("data/ChatHistory").absolute()
    preset_path: Path = Path("data/Presets").absolute()
    openai_proxy: str = None
    openai_api_base: str = None
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

    @validator('api_key')
    def api_key_validator(cls, v) -> List[str]:
        if not v:
            raise NoApiKeyError('请输入APIKEY')
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [v]
        raise ApiKeyError('请输入正确的APIKEY')


plugin_config: Config = Config.parse_obj(get_driver().config)
