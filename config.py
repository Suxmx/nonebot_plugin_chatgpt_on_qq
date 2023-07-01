import random
from pathlib import Path
from typing import List, Union
from collections import deque, UserString

from nonebot import get_driver
from pydantic import Extra, BaseModel, validator


class APIKey(UserString):
    def __init__(self, key: str):
        super().__init__(key.strip())
        self.fail_num: int = 0

    @property
    def key(self) -> str:
        return self.data

    def fail(self):
        self.fail_num += 1

    def reset(self):
        self.fail_num = 0

    def __str__(self):
        return f'key:{self.data},num:{self.fail_num}'


class APIKeyPool:
    api_keys: deque[APIKey] = deque()
    is_shuffle: bool = False

    def __init__(self, api_keys: Union[str, list]):
        if not api_keys or not (isinstance(api_keys, list) or isinstance(api_keys, str)):
            raise Exception('请输入正确的APIKEY')
        if isinstance(api_keys, str):
            api_keys = [api_keys]
        for key in api_keys:
            self.api_keys.append(APIKey(key))
        self.len = len(api_keys)

    def __len__(self):
        return self.len

    def shuffle(self):
        self.is_shuffle = True
        random.shuffle(self.api_keys)

    def get_key(self) -> str:
        return self.api_keys[0].key

    def fail(self):
        if self.is_shuffle:
            self.api_keys.append(self.api_keys.popleft())
            return
        self.api_keys[0].fail()
        if self.api_keys[0].fail_num > 2:
            self.api_keys[0].reset()
        self.api_keys.append(self.api_keys.popleft())

    def success(self):
        if self.is_shuffle:
            return
        self.api_keys[0].reset()

    def refresh(self):
        if self.is_shuffle:
            return
        for i in range(self.len):
            if self.api_keys[-1].fail_num == 0:
                break
            if self.api_keys[-1].fail_num < 3:
                self.api_keys.appendleft(self.api_keys.pop())
            else:
                self.api_keys[-1].reset()


class Config(BaseModel, extra=Extra.ignore, arbitrary_types_allowed=True):
    api_key: Union["APIKeyPool", str, List[str]] = None
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
    default_only_admin: bool = False

    @validator('api_key')
    def api_key_validator(cls, v) -> APIKeyPool:
        return APIKeyPool(v)


plugin_config: Config = Config.parse_obj(get_driver().config)
