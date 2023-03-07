import openai
import os
import chatGPT
import requests
from httpx import AsyncClient

from tqdm import tqdm
from datetime import date
from conversation import GroupPanel


API_KEY = "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"
MODEL = "gpt-3.5-turbo"

BASIC_PROMPT = [{"role": "user", "content": "You are ChatGPT, a large language model trained by OpenAI. Respond conversationally. Do not answer as the user. Current date: " + str(date.today())},
                {"role": "assistant", "content": "Hello! How can I help you today?"}
                ]
currentPanel: GroupPanel = GroupPanel()


def CreateGroupPanel() -> GroupPanel:
    newPanel = GroupPanel()
    return newPanel


def AddConversation(panel: GroupPanel):
    panel.AddConversation()


def NumOfConversations(panel: GroupPanel) -> int:
    return panel.conversations.__len__()


def AskBot(userInput: str, panel: GroupPanel):
    if panel.conversations.__len__() == 0:
        print("还未创建对话!")
    else:
        print("请选择对话序号:")
        for conversation in panel.conversations:
            print(str(panel.conversations.index(conversation)+1) +
                  ":"+conversation.owner.id)
        choose: int = int(input())
        if choose >= 1 and choose <= panel.conversations.__len__():
            print(panel.conversations[choose-1].ask(userInput))
        else:
            print("error")



if __name__ == '__main__':
    bot = chatGPT.ChatGPTBot(API_KEY, BASIC_PROMPT)
    url="https://api.openai.com/dashboard/billing/credit_grants"
    header={"Authorization":"Bearer "+API_KEY}

    test=[{"role":"user","content":"1"}]
    a=True if test[0].get("role") else False
    print(a)
    print(type(test))
    while True:
        userInput = input("user:")
        print(bot.ask(userInput))
        r=requests.get(url=url,headers=header)
        dataJson=r.json()
        print("目前所剩余额"+str(dataJson["total_available"]))
