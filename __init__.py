import json
import re
from json import JSONDecodeError
from typing import Optional, Dict, List

import openai
from nonebot import get_driver
from nonebot.adapters.onebot.v11 import (Bot,
                                         Event, MessageEvent,
                                         GroupMessageEvent, PrivateMessageEvent,
                                         GROUP_ADMIN, GROUP_OWNER)
from nonebot.log import logger
from nonebot.plugin import on_regex
from nonebot.params import ArgPlainText
from nonebot.permission import SUPERUSER, Permission
from nonebot.plugin import PluginMetadata

from .config import Config
from .conversation import Conversation, GroupPanel, presets_str
from .custom_errors import NoApiKeyError

__usage__: str = (
        "太长不看版:\n"
        + "先用/chat create命令,选择模板来创建对话,随后/talk 内容 来对话\n\n"
        + "/chat :获取菜单\n"
        + "/chat create :利用模板创建一个对话并加入\n"
        + "/talk <内容> :在当前的对话进行聊天\n"
        + "/chat list :获得当前已创建的对话列表\n"
        + "/chat join 序号(指/chat list中的序号) :参与list中的某个对话\n"
        + "/chat create (prompt) :自定义prompt来创建一个新的对话\n"
        + "/chat delete 序号(指/chat list中的序号) :删除list中的某个对话\n"
        + "/chat dump :导出当前对话的历史记录json\n"
)
__plugin_meta__ = PluginMetadata(
    name="多功能ChatGPT插件",
    description="基于chatGPT-3.5-turbo API的nonebot插件",
    usage=__usage__,
    config=Config,
    extra={
        "License": "BSD License",
        "Author": "颜曦",
        "version": "1.3.0",
    },
)

plugin_config: Config = Config.parse_obj(get_driver().config.dict())
temperature: float = plugin_config.temperature
allow_private: bool = plugin_config.allow_private
# 因为电脑端的qq在输入/chat xxx时候经常被转换成表情，所以支持自定义指令前缀替换"chat"
change_chat_to: str = plugin_config.change_chat_to
pattern_str = f'(chat|{change_chat_to})' if change_chat_to else 'chat'


async def _allow_private_checker(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) or allow_private


ALLOW_PRIVATE = Permission(_allow_private_checker)

Chat = on_regex(r"^/talk\s+.+", permission=ALLOW_PRIVATE)  # 聊天
CallMenu = on_regex(rf"^/{pattern_str}$", permission=ALLOW_PRIVATE)  # 呼出菜单
ShowList = on_regex(rf"^/{pattern_str}\s+list\s*$", permission=ALLOW_PRIVATE)  # 展示群聊天列表
Join = on_regex(rf"^/{pattern_str}\s+join\s+\d+", permission=ALLOW_PRIVATE)  # 加入对话
Delete = on_regex(rf"^/{pattern_str}\s+delete\s+\d+", permission=ALLOW_PRIVATE)  # 删除对话
Dump = on_regex(rf"^/{pattern_str}\s+dump$", permission=ALLOW_PRIVATE)  # 导出json
CreateConversationWithPrompt = on_regex(rf"^/{pattern_str}\s+create\s+.+$", permission=ALLOW_PRIVATE)  # 利用自定义prompt创建对话
CreateConversationWithTemplate = on_regex(rf"^/{pattern_str}\s+create$", permission=ALLOW_PRIVATE)  # 利用模板创建对话
CreateConversationWithJson = on_regex(rf"^/{pattern_str}\s+json$", permission=ALLOW_PRIVATE)  # 利用json创建对话

groupPanels: Dict[int, GroupPanel] = {}
privateConversations: Dict[int, Conversation] = {}


@Dump.handle()
async def _(event: Event):
    userId: int = int(event.get_user_id())
    userConver: Optional["Conversation"] = None
    if isinstance(event, GroupMessageEvent):
        groupId: int = event.group_id
        groupPanel = groupPanels.get(groupId)
        if groupPanel:
            userConver: Conversation = groupPanel.userInConversation.get(
                userId)
    else:
        userConver: Conversation = privateConversations.get(userId)
    if userConver:
        await Dump.finish(userConver.dumpJson())


@Chat.handle()
async def _(event: Event):
    msg = event.get_plaintext()
    userInput: str = re.sub(r"^/talk\s+", '', msg)
    if not userInput:
        await Chat.finish("输入不能为空!", at_sender=True)
    if isinstance(event, GroupMessageEvent):
        groupId: int = event.group_id
        userId: int = int(event.get_user_id())
        groupPanel: GroupPanel = groupPanels.setdefault(groupId, GroupPanel())
        if not groupPanels.get(groupId).userInConversation.get(userId):  # 若没有对话则先自动创建一个
            try:
                newConversation: Conversation = Conversation.CreateWithTemplate("1", userId)
            except KeyError:
                await Chat.finish("自动创建失败!请检查模板是否存在", at_sender=True)
            await Chat.send(f"自动创建{newConversation.name}成功", at_sender=True)
            groupPanel.userInConversation[userId] = newConversation
            groupPanel.conversations.append(newConversation)
            fin_conversation: Conversation = newConversation

        else:  # 获取GroupPanel以及用户所在的对话
            userConversation: Conversation = groupPanel.userInConversation.get(
                userId)
            fin_conversation: Conversation = userConversation
        try:
            answer: str = await fin_conversation.ask(userInput, temperature)
            await fin_conversation.GroupAutoSave(groupId)
        except ConnectionError:
            logger.error('连接错误...')
            await Chat.finish('连接错误...')
        except openai.InvalidRequestError as e:
            await Chat.finish(str(e))
        await Chat.finish(answer, at_sender=True)

    if isinstance(event, PrivateMessageEvent):
        userId: int = int(event.get_user_id())
        if not privateConversations.get(userId):  # 自动创建
            newConversation: Optional["Conversation"] = None
            try:
                newConversation = Conversation.CreateWithTemplate("1", userId)
            except KeyError:
                await Chat.finish("自动创建失败!请检查模板是否存在")
            await Chat.send(f"自动创建{newConversation.name}成功", at_sender=True)
            privateConversations[userId] = newConversation
            fin_conversation: Conversation = newConversation

        else:
            userConversation: Conversation = privateConversations.get(userId)
            fin_conversation: Conversation = userConversation
        try:
            answer = await fin_conversation.ask(userInput, temperature)
            await Chat.send(answer)
            await fin_conversation.PrivateAutoSave()
        except ConnectionError:
            logger.error('连接错误...')
            await Chat.finish('连接错误...')
        except openai.InvalidRequestError as e:
            await Chat.finish(str(e))


@Join.handle()
async def _(event: Event):
    msg = event.get_plaintext()
    msg = re.sub(rf"^/{pattern_str}\s+join\s+", '', msg)
    conversation_id = int(msg)
    if isinstance(event, GroupMessageEvent):
        groupPanel = groupPanels.get(event.group_id)
        if not groupPanel:
            await Join.finish("本群尚未创建过对话!请用/chat create命令来创建对话!", at_sender=True)
        if conversation_id < 1 or conversation_id > len(groupPanel.conversations):
            await Join.finish("序号超出!", at_sender=True)
        userId: int = int(event.get_user_id())
        fin_conversation = groupPanel.conversations[conversation_id - 1]
        groupPanel.userInConversation[userId] = fin_conversation
        await Join.finish(f"加入对话{conversation_id}成功!", at_sender=True)
    else:
        await Join.finish("私聊中无法加入对话!")


@CallMenu.handle()
async def _():
    menu: str = __usage__
    await CallMenu.finish(menu, at_sender=True)


@Delete.handle()
async def _(bot: Bot, event: Event):
    msg = event.get_plaintext()
    msg = re.sub(rf"^/{pattern_str}\s+delete\s+", '', msg)
    conversation_id = int(msg)
    if isinstance(event, GroupMessageEvent):
        groupPanel = groupPanels.get(event.group_id)
        if not groupPanel:
            await Join.finish("本群尚未创建过对话!", at_sender=True)
        if conversation_id < 1 or conversation_id > len(groupPanel.conversations):
            await Join.finish("序号超出!", at_sender=True)
        userId: int = int(event.get_user_id())
        perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
        if groupPanel.conversations[conversation_id - 1].owner.id == userId or perm_check:
            conver = groupPanel.conversations[conversation_id - 1]
            jointUser: List[int] = []
            for user, _conversation in groupPanel.userInConversation.items():
                if conver == _conversation:
                    jointUser.append(user)
            for user in jointUser:
                groupPanel.userInConversation.pop(user)

            groupPanel.conversations.pop(conversation_id - 1)
            await Delete.finish("删除成功!")
        else:
            await Delete.finish("您不是该对话的创建者或管理员!")
    else:
        privateConversations.pop(int(event.get_user_id()))
        await Delete.finish("已删除当前对话")


# 暂时已完成


@ShowList.handle()
async def _(event: Event):
    if isinstance(event, GroupMessageEvent):
        curPanel: GroupPanel = groupPanels.get(event.group_id)
        if not curPanel:
            await ShowList.finish("本群尚未创建过对话", at_sender=True)
        elif len(curPanel.conversations) == 0:
            await ShowList.finish("本群对话已全部被清除", at_sender=True)
        else:
            msg: str = "\n"
            for _conversation in curPanel.conversations:
                msg += f"{curPanel.conversations.index(_conversation) + 1}. {_conversation.name} " \
                       f"创建者:{_conversation.owner.id}\n"
            await ShowList.finish(msg, at_sender=True)
    elif isinstance(event, PrivateMessageEvent):
        await ShowList.finish("私聊中无法展示列表(最多只有一个对话)")


# 暂时完成


@CreateConversationWithPrompt.handle()
async def _(event: Event):
    msg = event.get_plaintext()
    customPrompt: str = re.sub(rf"^/{pattern_str}\s+create\s*", '', msg)  # 获取用户自定义prompt
    if customPrompt:
        userID: int = int(event.get_user_id())
        try:
            newConversation: Conversation = Conversation.CreateWithStr(
                customPrompt, userID, customPrompt[:5])
        except NoApiKeyError:
            await CreateConversationWithPrompt.finish("请机器人管理员在设置中添加APIKEY！")
        if isinstance(event, GroupMessageEvent):  # 当在群聊中时
            groupId: int = event.group_id
            group_panel: GroupPanel = groupPanels.setdefault(groupId, GroupPanel())
            group_panel.conversations.append(newConversation)
            group_panel.userInConversation[userID] = newConversation
            await CreateConversationWithPrompt.finish(f"创建成功!", at_sender=True)

        elif isinstance(event, PrivateMessageEvent):  # 当在私聊中时
            if privateConversations[userID]:
                await CreateConversationWithPrompt.finish("已存在一个对话,请先删除")
            else:
                privateConversations[userID] = Conversation.CreateWithStr(
                    customPrompt, userID, customPrompt[:6])
                await CreateConversationWithPrompt.finish(f"用户{str(userID)}创建成功")
    else:  # 若prompt全为空
        await CreateConversationWithPrompt.finish("输入prompt不能为空格!")


@CreateConversationWithTemplate.handle()
async def CreateConversation():
    await CreateConversationWithTemplate.send(presets_str, at_sender=True)


# 暂时完成


@CreateConversationWithTemplate.got(key="template")
async def Create(event: Event, template_id: str = ArgPlainText("template")):
    userId: int = int(event.get_user_id())
    if isinstance(event, PrivateMessageEvent):
        if privateConversations.get(userId):
            await CreateConversationWithTemplate.finish("已存在一个对话，请先删除该对话!")
    if not template_id.isdigit():
        await CreateConversationWithTemplate.reject("输入ID无效!")

    newConversation: Optional["Conversation"] = None
    try:
        newConversation = Conversation.CreateWithTemplate(template_id, userId)
    except NoApiKeyError:
        await CreateConversationWithTemplate.finish("请机器人管理员在设置中添加APIKEY！")
    if newConversation is None:
        await CreateConversationWithTemplate.finish("输入ID无效!")
    await CreateConversationWithTemplate.send(f"使用模板{template_id}创建{newConversation.name}对话成功!",
                                              at_sender=True)
    if isinstance(event, GroupMessageEvent):
        groupId: int = event.group_id
        group_panel: GroupPanel = groupPanels.setdefault(groupId, GroupPanel())

        group_panel.userInConversation[userId] = newConversation
        group_panel.conversations.append(newConversation)
    else:
        privateConversations[userId] = newConversation


@CreateConversationWithJson.handle()
async def CreateConversation():
    pass


@CreateConversationWithJson.got("jsonStr", "请直接输入json")
async def GetJson(event: Event, jsonStr: str = ArgPlainText("jsonStr")):
    try:
        history = json.loads(jsonStr)
    except JSONDecodeError:
        logger.error("json字符串错误!")
        await CreateConversationWithJson.reject("Json错误!")
    if not history[0].get("role"):
        await CreateConversationWithJson.reject("Json错误!")
    userId: int = int(event.get_user_id())
    try:
        newConversation: Conversation = Conversation(history, userId, history[0].get('content', '')[:6])
    except NoApiKeyError:
        await CreateConversationWithJson.finish("请机器人管理员在设置中添加APIKEY！")

    if isinstance(event, GroupMessageEvent):
        groupId: int = event.group_id
        group_panel: GroupPanel = groupPanels.setdefault(groupId, GroupPanel())
        group_panel.conversations.append(newConversation)
        group_panel.userInConversation[userId] = newConversation
        await CreateConversationWithJson.send("创建对话成功!", at_sender=True)
    elif isinstance(event, PrivateMessageEvent):
        privateConversations[userId] = newConversation
        await CreateConversationWithJson.send("创建对话成功!")
