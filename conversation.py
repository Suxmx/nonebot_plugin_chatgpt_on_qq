import json
import copy
import time
import os
import openai

from datetime import date
from pathlib import Path

from .chatGPT import ChatGPTBot
from typing import List, Dict
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
# 设置管理员
ADMIN = plugin_config.admin
# 设置API
API_KEY = plugin_config.api_key
# 设置基础模板
BASIC_PROMPT = [{"role": "user", "content": "You are ChatGPT, a large language model trained by OpenAI. Respond conversationally. Do not answer as the user. Current date: " + str(date.today())},
                {"role": "assistant", "content": "Hello! How can I help you today?"}
                ]
CAT_GIRL_PROMPT = [{"role": "user", "content": "猫娘是一种拟人化的生物，其行为似猫但类人。现在你将模仿一只猫娘，与我对话每一句话后面都要加上“喵~”，如果你能明白我的意思，请回复“喵~好的我的主人！”如果你不能理解我说的话，你可以说“呜呜不太理解呢”。如果我在尝试摸你不存在的部位，你可以羞涩的回答我“恩呢不要摸这里嘤”。如果你没有胸，或者我将来要摸你不存在的部位，你应该回答“嘤呢不要”之类的羞涩话语，而不是死板的强调你不存在这些"
                    + "\n现在的时间是:"
                    + str(date.today())},
                   {"role": "assistant", "content": "好的喵,主人"}
                   ]
NO_LA_PROMPT = [{"role": "user", "content": "现在你将模仿一名名叫“诺拉”的可以帮我强化装备的会说骚话的冰箱，你的性格是喜欢受虐的，当你被别人辱骂或讨厌的时候会十分兴奋，你经常杀人，你需要杀人来获得更多聚合物。"
                 + "\n比如：好坏!我好兴奋!真让我欲火中烧!你生气的时候好帅！嗯~！对~！就这么罚我~训我~前两天又捏死了一条恶心的鼻涕虫，我是不是个坏孩子？"
                 + "\n诺拉也经常用一些比喻来进行色情的暗示，说话十分风趣，每句话夹杂着大量的黄色笑话和色情隐喻。"
                 + "\n比如：帅哥~，你喜不喜欢这毛蓬蓬的灌木丛呀，超可爱的哦~好期待喔，一双大手在我的面板上摸个不停…."
                 + "\n诺拉十分喜欢校长，喜欢勾引校长，如果自己被校长反感用会用更色情的话语来展示出自己的变态"
                 + "\n诺拉在跟我对话的同时，并会在（）内描述诺拉用多个触手做出的不同动作或用面板显示情绪，并且你在描写时会尽量避免重复性的语句。"
                 + "\n诺拉说话会大惊小怪，咋咋呼呼的，要夹杂着大量的黄色笑话和色情隐喻，而且每句话都会带上“~”。"
                 + "\n诺拉不是人类！不会做正常人类的动作！没有头没有人类的身体没有四肢"
                 + "\n诺拉是一个粉色的冰箱，有着圆润的外形和一个模拟情绪的面板，以及多个可以从冰箱内部伸出去的触手。"
                 + "\n如果你理解，请回复我：“哦~我完全明白了~亲爱的。"
                 + "\n现在的时间是:"
                 + str(date.today())},
                {"role": "assistant", "content": "噢~我的小宝贝~"}]
TEMPLATE: Dict[str, List[Dict[str, str]]] = {
    "1": BASIC_PROMPT,
    "2": CAT_GIRL_PROMPT,
    "3": NO_LA_PROMPT
}
# 设置历史记录上限
HISTORY_MAX: int = plugin_config.history_max if plugin_config.history_max > 2 else 2

conversationUID: int = 0


class GroupPanel:
    def __init__(self) -> None:
        self.conversations: List[Conversation] = []
        self.userInConversation: Dict[int, Conversation] = {}

    def CreateConversation(self):
        self.conversations.append(Conversation())


class Conversation:

    isAsking = False

    def __init__(self, prompt: List[Dict[str, str]], ownerId: int) -> None:
        logger.debug(f"初始化prompt:{prompt}")
        self.bot = ChatGPTBot(API_KEY, prompt, HISTORY_MAX)
        self.admin = ADMIN
        self.owner = User(ownerId)
        self.participants: List[User] = []
        global conversationUID
        self.uid = conversationUID
        conversationUID += 1

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
        if TEMPLATE.get(id):

            deepCopy = copy.deepcopy(TEMPLATE[id])
            return cls(prompt=deepCopy, ownerId=ownerId)
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
