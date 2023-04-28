import os
import json
import copy
import time
from pathlib import Path
from typing import List, Dict, Optional

import openai
from nonebot import get_driver
from nonebot.log import logger

from .config import Config
from .chatGPT import ChatGPTBot
from .loadpresets import Preset, load_all_preset

plugin_config: Config = Config.parse_obj(get_driver().config.dict())
# 设置代理
proxy: Optional[str] = plugin_config.openai_proxy
api_base: Optional[str] = plugin_config.openai_api_base

if not proxy:
    logger.error("请设置代理!")
else:
    openai.proxy = {'http': f"http://{proxy}", 'https': f'http://{proxy}'}
if api_base:
    openai.api_base = api_base

# 设置保存路径
START_TIME: str = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
SAVE_PATH: Path = plugin_config.history_save_path.joinpath(START_TIME)
# 设置API
API_KEY: str = plugin_config.api_key
# 设置基础模板
preset_path: Path = plugin_config.preset_path
presets_list: List[Preset] = load_all_preset(preset_path)
presets_str: str = Preset.presets2str(presets_list)
templateDict: Dict[str, Preset] = {str(preset.preset_id): preset for preset in presets_list}

# 设置历史记录上限
HISTORY_MAX: int = plugin_config.history_max if plugin_config.history_max > 2 else 2

conversationUID: int = 0


class GroupPanel:
    def __init__(self) -> None:
        self.conversations: List[Conversation] = []
        self.userInConversation: Dict[int, Conversation] = {}


class Conversation:
    isAsking: bool = False
    name: str = ""

    def __init__(self, prompt: List[Dict[str, str]], ownerId: int, name: str = "") -> None:
        logger.debug(f"初始化prompt:{prompt}")
        self.bot: ChatGPTBot = ChatGPTBot(API_KEY, prompt, HISTORY_MAX)
        self.owner: User = User(ownerId)
        self.participants: List[User] = []
        global conversationUID
        self.uid: int = conversationUID
        conversationUID += 1
        self.name: str = name

    @classmethod
    def CreateWithStr(cls, customPrompt: str, ownerId: int, name: str = '') -> "Conversation":
        customPrompt = [{"role": "user", "content": customPrompt}, {
            "role": "assistant", "content": "好"}]
        return cls(customPrompt, ownerId, name)

    @classmethod
    def CreateWithJson(cls, jsonStr: str, ownerId: int, name: str = '') -> "Conversation":
        messages: List[Dict[str, str]] = json.loads(jsonStr)
        return cls(messages, ownerId, name)

    @classmethod
    def CreateWithTemplate(cls, template_id: str, ownerId: int) -> "Conversation":
        deepCopy: List[Dict[str, str]] = copy.deepcopy(templateDict[template_id].preset)
        return cls(prompt=deepCopy, ownerId=ownerId, name=templateDict[template_id].name)

    async def ask(self, userInput: str, temperature: float) -> str:
        return await self.bot.ask(userInput, temperature)

    def dumpJson(self) -> str:
        return self.bot.dumpJsonStr()

    async def GroupAutoSave(self, groupID: int) -> None:
        groupID = str(groupID)
        fileName: str = time.strftime(
            "%Y-%m-%d-%H-%M-%S", time.localtime()) + ".json"
        savePath: Path = SAVE_PATH.joinpath("GroupConversations").joinpath(
            str(groupID)).joinpath(str(self.owner.id)).joinpath(str(self.uid))
        if not savePath.exists():
            os.makedirs(savePath)
        savePath = savePath.joinpath(fileName)
        await self.AutoSave(savePath)

    async def PrivateAutoSave(self) -> None:
        fileName: str = time.strftime(
            "%Y-%m-%d-%H-%M-%S", time.localtime()) + ".json"
        savePath: Path = SAVE_PATH.joinpath(
            "PrivateConversations").joinpath(str(self.owner.id))
        if not savePath.exists():
            os.makedirs(savePath)
        savePath = savePath.joinpath(fileName)
        await self.AutoSave(savePath)

    async def AutoSave(self, path: Path) -> None:
        with open(path, "w", encoding="utf8") as f:
            try:
                json.dump(self.bot.prompt_manager.history,
                          f, ensure_ascii=False)
                logger.debug(f"auto save History json {path}")
            except Exception:
                logger.error("保存History json失败!")


class User:
    def __init__(self, userId: int) -> None:
        self.id = userId
