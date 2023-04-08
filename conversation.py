import json
import copy
import time
import os
import openai

from datetime import date
from pathlib import Path

from .chatGPT import ChatGPTBot
from .loadpresets import presetcls,loadall,listPresets,createdict
from typing import List
from nonebot import get_driver
from nonebot.log import logger

from .config import Config

plugin_config = Config.parse_obj(get_driver().config.dict())
# 设置代理
proxy = plugin_config.openai_proxy
api_base = plugin_config.openai_api_base

if proxy == None:
    logger.error("请设置代理!")
else:
    openai.proxy = {'http': f"http://{proxy}", 'https': f'http://{proxy}'}
if api_base != None:
    openai.api_base = api_base

# 设置保存路径
START_TIME = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
SAVE_PATH: Path = plugin_config.history_save_path.joinpath(START_TIME)
# 设置API
API_KEY = plugin_config.api_key
# 设置基础模板
preset_path=plugin_config.preset_path
loadedPresets=loadall(preset_path)
templateDict=createdict(presets=loadedPresets)
    
# 设置历史记录上限
HISTORY_MAX: int = plugin_config.history_max if plugin_config.history_max > 2 else 2

conversationUID: int = 0


class GroupPanel:
    def __init__(self) -> None:
        self.conversations: List[Conversation] = []
        self.userInConversation: dict[int:Conversation] = {}

    def CreateConversation(self):
        self.conversations.append(Conversation())


class Conversation:

    isAsking = False
    name=""
    def __init__(self, prompt: list[dict[str:str]], ownerId: int,name:str="") -> None:
        logger.debug(f"初始化prompt:{prompt}")
        self.bot = ChatGPTBot(API_KEY, prompt, HISTORY_MAX)
        self.owner = User(ownerId)
        self.participants: List[User] = []
        global conversationUID
        self.uid = conversationUID
        conversationUID += 1
        self.name=name

    @classmethod
    def CreateWithStr(cls, customPrompt: str, ownerId: int):
        customPrompt = [{"role": "user", "content": customPrompt}, {
            "role": "assistant", "content": "好"}]
        return cls(customPrompt, ownerId)

    @classmethod
    def CreateWithJson(cls, jsonStr: str, ownerId: int):
        messages = json.loads(jsonStr)
        return cls(messages, ownerId)

    @classmethod
    def CreateWithTemplate(cls, id, ownerId: int):
        if templateDict.get(id):
            deepCopy = copy.deepcopy(templateDict[id].preset)
            return cls(prompt=deepCopy, ownerId=ownerId,name=templateDict[id].name)
        else:
            return None

    def ask(self, userInput: str) -> str:
        answer = self.bot.ask(userInput)
        return answer

    def dumpJson(self):
        return self.bot.dumpJsonStr()

    async def GroupAutoSave(self, groupID: int):
        groupID = str(groupID)
        fileName: str = time.strftime(
            "%Y-%m-%d-%H-%M-%S", time.localtime())+".json"
        savePath: Path = SAVE_PATH.joinpath("GroupConversations").joinpath(
            str(groupID)).joinpath(str(self.owner.id)).joinpath(str(self.uid))
        if (not savePath.exists()):
            os.makedirs(savePath)
        savePath = savePath.joinpath(fileName)
        await self.AutoSave(savePath)

    async def PrivateAutoSave(self):
        fileName: str = time.strftime(
            "%Y-%m-%d-%H-%M-%S", time.localtime())+".json"
        savePath: Path = SAVE_PATH.joinpath(
            "PrivateConversations").joinpath(str(self.owner.id))
        if not savePath.exists():
            os.makedirs(savePath)
        savePath = savePath.joinpath(fileName)
        await self.AutoSave(savePath)

    async def AutoSave(self, path: Path):
        with open(path, "w", encoding="GB2312") as f:
            try:
                json.dump(self.bot.prompt_manager.history,
                          f, ensure_ascii=False)
                logger.debug("save")
            except UnicodeEncodeError:
                json.dump(self.bot.prompt_manager.history,
                          f, ensure_ascii=True)
            except:
                logger.error("保存Historyjson失败!")


class User:
    def __init__(self, userId: str) -> None:
        self.id = userId
def listpresets()->str:
    return listPresets(loadedPresets)
