import openai
import os
import tiktoken
import json
from datetime import date
from .custom_errors import OverMaxTokenLengthError, NoResponseError,NoApiKeyError
from nonebot.log import logger
#import nonebot_plugin_tuan_chatgpt


ENCODER = tiktoken.get_encoding("gpt2")
MAX_TOKEN = 4000
MAX_INPUT = 2000
MODEL = "gpt-3.5-turbo"




class PromptManager:
    def __init__(self,  basic_prompt, max_input: int = MAX_INPUT) -> None:
        self.history: list[dict[str:str]] = basic_prompt
        self.max_input = max_input
        self.basic_len=len(basic_prompt)
        self.count=0

    def check_token_length(self, dicts) -> int:
        msgs: str = ""
        for dict in dicts:
            msgs += (dict["content"])+(dict["role"])+":::\n\n\n" #人工补正
        # print("预估长度："+str(len(ENCODER.encode(msgs))))
        return len(ENCODER.encode(msgs))

    def construct_prompt(
            self,
            new_prompt: str,
    ) -> list[dict[str:str]]:
        self.history.append({"role": "user", "content": new_prompt})
        if (self.check_token_length(dicts=self.history) > self.max_input):
            if len(self.history) == self.basic_len+1:
                raise OverMaxTokenLengthError("用户输入token长度超过最大值")
            elif len(self.history) > self.basic_len+1:
                self.history.pop(self.basic_len)
                self.history.pop(self.basic_len)
                self.history.pop()
                
            return self.construct_prompt(new_prompt)
        return self.history

    def add_to_history(self, completion):
        role = completion["choices"][0]["message"]["role"]
        content = completion["choices"][0]["message"]["content"]
        self.history.append({"role": role, "content": content})
        #logger.debug(self.history)
    def dumpJsonStr(self):
        self.count=self.count+1
        jsonName=f"history{self.count}.json"
        #with open(jsonName,"w",encoding="GB2312") as f:
        try:
            jsonStr=json.dumps(self.history,ensure_ascii=False)
        except UnicodeEncodeError:
            jsonStr=json.dumps(self.history,ensure_ascii=True)
        return jsonStr
        



class ChatGPTBot:
    def __init__(self, api_key: str, basic_prompt) -> None:
        if api_key is not "NoKey":
            openai.api_key = api_key
        else:
            raise NoApiKeyError("未设置ApiKey")
        self.prompt_manager = PromptManager(basic_prompt=basic_prompt)
        self.talk_count=0

    def ask(
        self,
        user_input: str,
        temperature: float = 0.5,
    ) -> dict:

        try:
            completion = self._get_completion(user_input, temperature)
            self._process_completion(completion=completion)
            return completion["choices"][0]["message"]["content"]
        except:
            self.prompt_manager.history.pop()
            raise ConnectionError
        

    def _get_completion(
            self,
            user_input: str,
            temperature: float = 0.5
    ):

        return openai.ChatCompletion.create(
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
        # self.talk_count+=1
        # name=str(f"history{self.talk_count}.json")
        # with open(name,"w",encoding="GB2312") as f:
        #     try:
        #         json.dump(self.prompt_manager.history,f,ensure_ascii=False)
        #     except UnicodeEncodeError:
        #         json.dump(self.prompt_manager.history,f,ensure_ascii=True)
        #     except:
        #         logger.error("保存json失败!")
        # print("实际使用tokens:"+str(completion["usage"]["prompt_tokens"]))
    def dumpJsonStr(self):
        return self.prompt_manager.dumpJsonStr()
