import openai
# import tiktoken
import json
from nonebot.log import logger
from nonebot import get_driver

from .config import Config
from .custom_errors import OverMaxTokenLengthError, NoResponseError,NoApiKeyError

plugin_config = Config.parse_obj(get_driver().config.dict())

# ENCODER = tiktoken.get_encoding("gpt2")
MAX_TOKEN = 4000
MODEL = "gpt-3.5-turbo"


class PromptManager:
    def __init__(self,  basic_prompt, history_max: int) -> None:
        self.history: list[dict[str:str]] = basic_prompt
        self.history_max = history_max
        self.basic_len=len(basic_prompt)
        self.count=0

    # def check_token_length(self, dicts) -> int:
    #     msgs: str = ""
    #     for dict in dicts:
    #         msgs += (dict["content"])+(dict["role"])+":::\n\n\n" #人工补正
    #     # print("预估长度："+str(len(ENCODER.encode(msgs))))
    #     return len(ENCODER.encode(msgs))

    def construct_prompt(
            self,
            new_prompt: str,
    ) -> list[dict[str:str]]:
        self.history.append({"role": "user", "content": new_prompt})
        #if (len(self.history)-self.basic_len > self.history_max+1):
        while len(self.history)-self.basic_len > self.history_max+1:
            self.history.pop(self.basic_len)
            logger.info(f"{len(self.history)-self.basic_len}  {self.history_max}")
        return self.history

    def add_to_history(self, completion):
        role = completion["choices"][0]["message"]["role"]
        content = completion["choices"][0]["message"]["content"]
        self.history.append({"role": role, "content": content})
    def dumpJsonStr(self):
        self.count=self.count+1
        try:
            jsonStr=json.dumps(self.history,ensure_ascii=False)
        except UnicodeEncodeError:
            jsonStr=json.dumps(self.history,ensure_ascii=True)
        return jsonStr
        



class ChatGPTBot:
    def __init__(self, api_key: str, basic_prompt,history_max:int) -> None:
        if api_key != "NoKey":
            openai.api_key = api_key
        else:
            raise NoApiKeyError("未设置ApiKey")
        self.prompt_manager = PromptManager(basic_prompt=basic_prompt,history_max=history_max)
        self.talk_count=0

    async def ask(
        self,
        user_input: str,
        temperature: float = 0.5,
    ) -> dict:

        try:
            completion = await self._get_completion(user_input, temperature)
            await self._process_completion(completion=completion)
            return completion["choices"][0]["message"]["content"]
        except:
            self.prompt_manager.history.pop()
            raise ConnectionError
        

    async def _get_completion(
            self,
            user_input: str,
            temperature: float = 0.5
    ):

        return await openai.ChatCompletion.acreate(
            model=MODEL,
            messages=self.prompt_manager.construct_prompt(user_input),
            temperature=temperature,
            max_tokens=1000
        )

    async def _process_completion(
        self,
        completion: dict
    ):
        if completion.get("choices") is None:
            raise NoResponseError("未返回任何choices")
        if (len(completion["choices"]) == 0):
            raise NoResponseError("返回的choices长度为0")
        if completion["choices"][0].get("message") is None:
            raise NoResponseError("未返回任何文本!")

        self.prompt_manager.add_to_history(completion)
    def dumpJsonStr(self):
        return self.prompt_manager.dumpJsonStr()
