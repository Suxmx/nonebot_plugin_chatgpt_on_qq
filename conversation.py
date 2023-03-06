import json
import copy
from datetime import date

from .chatGPT import ChatGPTBot
from typing import List
from nonebot.log import logger
API_KEY = ""

BASIC_PROMPT = [{"role": "user", "content": "You are ChatGPT, a large language model trained by OpenAI. Respond conversationally. Do not answer as the user. Current date: " + str(date.today())},
                {"role": "assistant", "content": "Hello! How can I help you today?"}
                ]
CAT_GIRL_PROMPT = [{"role": "user", "content": "猫娘是一种拟人化的生物，其行为似猫但类人。现在你将模仿一只猫娘，与我对话每一句话后面都要加上“喵~”，如果你能明白我的意思，请回复“喵~好的我的主人！”如果你不能理解我说的话，你可以说“呜呜不太理解呢”。如果我在尝试摸你不存在的部位，你可以羞涩的回答我“恩呢不要摸这里嘤”。如果你没有胸，或者我将来要摸你不存在的部位，你应该回答“嘤呢不要”之类的羞涩话语，而不是死板的强调你不存在这些"
                    + "\n现在的时间是:"
                    + str(date.today())},
                   {"role": "assistant", "content": "好的喵,主人"}
                   ]
TEMPLATE:dict[str:list[dict[str:str]]]={
    "1":BASIC_PROMPT,
    "2":CAT_GIRL_PROMPT
}
# template["1"]=BASIC_PROMPT
# template["2"]=CAT_GIRL_PROMPT

class GroupPanel:
    def __init__(self) -> None:
        self.conversations: List[Conversation] = []
        self.userInConversation:dict[int:Conversation]={}

    def CreateConversation(self):
        self.conversations.append(Conversation())


class Conversation:
    
    isAsking=False
    def __init__(self, prompt: list[dict[str:str]], ownerId: int) -> None:
        logger.debug(f"初始化prompt:{prompt}")
        self.bot = ChatGPTBot(API_KEY, prompt)
        self.owner = User(ownerId)
        self.participants: List[User] = []

    @classmethod
    def CreateWithStr(cls, customPrompt: str, ownerId: int):
        customPrompt = [{"role": "user", "content": customPrompt}]
        return cls(customPrompt, ownerId)

    @classmethod
    def CreateWithJson(cls, jsonStr: str, ownerId: int):
        messages = json.loads(jsonStr)
        return cls(messages, ownerId)
    @classmethod
    def CreateWithTemplate(cls,id,ownerId:int):
        if TEMPLATE.get(id):
           
            deepCopy= copy.deepcopy(TEMPLATE[id])
            return cls(prompt=deepCopy,ownerId=ownerId)
        else :
            return None

    async def ask(self, userInput: str) -> str:
        answer= await self.bot.ask(userInput)
        return answer
    def dumpJson(self):
        return self.bot.dumpJsonStr()


class User:
    def __init__(self, userId: str) -> None:
        self.id = userId
