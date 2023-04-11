import json
import re
import openai

from nonebot import get_driver
from nonebot.adapters.onebot.v11 import (Bot,
                                         Event,
                                         GroupMessageEvent, PrivateMessageEvent,
                                         GROUP_ADMIN, GROUP_OWNER)
from nonebot.log import logger
from nonebot.plugin import on_regex, on_fullmatch
from nonebot.params import ArgPlainText
from nonebot.permission import SUPERUSER

from .conversation import Conversation, GroupPanel,listpresets
from .custom_errors import NoApiKeyError

Chat = on_regex(r"^/talk\s+.+")  # 聊天
CallMenu = on_fullmatch("/chat")  # 呼出菜单
ShowList = on_regex(r"^/chat\s+list\s*$")  # 展示群聊天列表
Join = on_regex(r"^/chat\s+join\s+\d+")  # 加入对话
Delete = on_regex(r"^/chat\s+delete\s+\d+")  # 删除对话
Dump = on_regex(r"^/chat\s+dump$")  # 导出json
CreateConversationWithPrompt = on_regex(r"^/chat\s+create\s+.+$")# 利用自定义prompt创建对话
CreateConversationWithTemplate = on_regex(r"^/chat\s+create$")# 利用模板创建对话
CreateConversationWithJson = on_regex(r"^/chat\s+json$")# 利用json创建对话

groupPanels: dict[int:GroupPanel] = {}
privateConversations: dict[int, Conversation] = {}


@Dump.handle()
async def _(event: Event):
    userId = event.get_user_id()
    if isinstance(event, GroupMessageEvent):
        groupId = event.group_id
        groupPanel = groupPanels.get(groupId)
        if groupPanel:
            userConver: Conversation = groupPanel.userInConversation.get(
                userId)
    else:
        userConver: Conversation = privateConversations.get(userId)
    if userConver:
        await Dump.finish(userConver.dumpJson())


@Chat.handle()
async def _(bot: Bot, event: Event):
    msg = event.get_plaintext()
    userInput: str = re.sub(r"^/talk\s+", '', msg)
    if not userInput:
        await Chat.finish("输入不能为空!", at_sender=True)
    if isinstance(event, GroupMessageEvent):
        groupId = event.group_id
        userId = event.get_user_id()
        if not groupPanels.get(groupId) or not groupPanels.get(groupId).userInConversation.get(userId):# 若没有对话则先自动创建一个
            try:
                newConversation = Conversation.CreateWithTemplate("1", userId)
            except:
                await Chat.finish("自动创建失败!请检查模板是否存在", at_sender=True)
            await Chat.send(f"自动创建{newConversation.name}成功",at_sender=True)
            groupPanels[event.group_id] = GroupPanel()
            groupPanels[event.group_id].userInConversation[userId] = newConversation
            groupPanels[event.group_id].conversations.append(newConversation)
            try:
                answer = await newConversation.ask(userInput)
                await newConversation.GroupAutoSave(groupId)
            except openai.InvalidRequestError as e:
                await Chat.finish(str(e))
            
        else:  # 获取GroupPanel以及用户所在的对话
            groupPanel = groupPanels.get(groupId)
            userConversation: Conversation = groupPanel.userInConversation.get(
                userId)
            try:
                answer = await userConversation.ask(userInput)
                await userConversation.GroupAutoSave(groupId)
            except openai.InvalidRequestError as e:
                await Chat.finish(str(e))

        await Chat.finish(answer, at_sender=True)
    if isinstance(event, PrivateMessageEvent):
        userId = event.get_user_id()
        if not privateConversations.get(userId):# 自动创建
            newConversation=None
            try:
                newConversation = Conversation.CreateWithTemplate("1", userId)
            except:
                await Chat.finish("自动创建失败!请检查模板是否存在")
            if newConversation is not None:
                await Chat.send(f"自动创建{newConversation.name}成功",at_sender=True)
                privateConversations[userId] = newConversation
                try:
                    answer = await newConversation.ask(userInput)
                    await Chat.send(answer)
                    await newConversation.PrivateAutoSave()
                except openai.InvalidRequestError as e:
                    await Chat.finish(str(e))
        else:
            userConversation: Conversation = privateConversations.get(userId)
            try:
                answer = await userConversation.ask(userInput)
                await Chat.send(answer)
                await userConversation.PrivateAutoSave()
            except openai.InvalidRequestError as e:
                    await Chat.finish(str(e))



@Join.handle()
async def _(event: Event):
    msg = event.get_plaintext()
    msg = re.sub(r"^/chat\s+join\s+", '', msg)
    id = int(msg)
    if isinstance(event, GroupMessageEvent):
        groupPanel = groupPanels.get(event.group_id)
        if not groupPanel:
            await Join.finish("本群尚未创建过对话!请用/chat create命令来创建对话!", at_sender=True)
        if id < 1 or id > len(groupPanel.conversations):
            await Join.finish("序号超出!", at_sender=True)
        userId = event.get_user_id()
        conversation = groupPanel.conversations[id-1]
        groupPanel.userInConversation[userId] = conversation
        await Join.finish(f"加入对话{id}成功!", at_sender=True)
    else:
        await Join.finish("私聊中无法加入对话!")


@CallMenu.handle()
async def _(bot: Bot, event: Event):
    menu: str = (
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
    await CallMenu.finish(menu, at_sender=True)


@Delete.handle()
async def _(bot: Bot, event: Event):
    msg = event.get_plaintext()
    msg = re.sub(r"^/chat\s+delete\s+", '', msg)
    id = int(msg)
    if isinstance(event, GroupMessageEvent):
        groupPanel = groupPanels.get(event.group_id)
        if not groupPanel:
            await Join.finish("本群尚未创建过对话!", at_sender=True)
        if id < 1 or id > len(groupPanel.conversations):
            await Join.finish("序号超出!", at_sender=True)
        userId = event.get_user_id()
        perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
        if groupPanel.conversations[id-1].owner.id == userId or perm_check:
            conver = groupPanel.conversations[id-1]
            jointUser: list[int] = []
            for user, conversation in groupPanel.userInConversation.items():
                if conver == conversation:
                    jointUser.append(user)
            for user in jointUser:
                groupPanel.userInConversation.pop(user)

            groupPanel.conversations.pop(id-1)
            await Delete.finish("删除成功!")
        else:
            await Delete.finish("您不是该对话的创建者或管理员!")
    else:
        privateConversations.pop(event.get_user_id())
        await Delete.finish("已删除当前对话")
# 暂时已完成


@ShowList.handle()
async def _(bot: Bot, event: Event):
    if isinstance(event, GroupMessageEvent):
        curPanel: GroupPanel = groupPanels.get(event.group_id)
        if not curPanel:
            await ShowList.finish("本群尚未创建过对话", at_sender=True)
        elif len(curPanel.conversations) == 0:
            await ShowList.finish("本群对话已全部被清除", at_sender=True)
        else:
            msg: str = "\n"
            for conversation in curPanel.conversations:
                msg += f"{curPanel.conversations.index(conversation)+1} 创建者:{conversation.owner.id}\n"
            await ShowList.finish(msg, at_sender=True)
    elif isinstance(event, PrivateMessageEvent):
        await ShowList.finish("私聊中无法展示列表(最多只有一个对话)")

# 暂时完成


@CreateConversationWithPrompt.handle()
async def _(bot: Bot, event: Event):
    msg = event.get_plaintext()
    customPrompt: str = re.sub(r"^/chat\s+create\s*", '', msg)  # 获取用户自定义prompt
    if customPrompt:
        userID = event.get_user_id()
        try:
            newConversation = Conversation.CreateWithStr(
                customPrompt, userID)
        except NoApiKeyError:
            await CreateConversationWithPrompt.finish("请机器人管理员在设置中添加APIKEY！")
        if isinstance(event, GroupMessageEvent):  # 当在群聊中时
            if not groupPanels.get(event.group_id):  # 没有时创建新的groupPanel
                groupPanels[event.group_id] = GroupPanel()
            groupPanels[event.group_id].conversations.append(newConversation)
            groupPanels[event.group_id].userInConversation[userID] = newConversation
            await CreateConversationWithPrompt.finish(f"创建成功!", at_sender=True)

        elif isinstance(event, PrivateMessageEvent):  # 当在私聊中时
            if privateConversations[userID]:
                await CreateConversationWithPrompt.finish("已存在一个对话,请先删除")
            else:
                privateConversations[userID] = Conversation.CreateWithStr(
                    customPrompt, userID)
                await CreateConversationWithPrompt.finish(f"用户{str(userID)}创建成功")
    else:  # 若prompt全为空
        await CreateConversationWithPrompt.finish("输入prompt不能为空格!")


@CreateConversationWithTemplate.handle()
async def CreateConversation(event: Event):
    ans=listpresets()
    await CreateConversationWithTemplate.send(ans, at_sender=True)

# 暂时完成


@CreateConversationWithTemplate.got(key="template")
async def Create(event: Event, id: str = ArgPlainText("template")):
    ifGroup = True
    userId = event.get_user_id()
    if isinstance(event, PrivateMessageEvent):
        ifGroup = False
        if privateConversations.get(userId):
            await CreateConversationWithTemplate.finish("已存在一个对话，请先删除该对话!")
    if not id.isdigit():
        await CreateConversationWithTemplate.reject("输入ID无效!")
    newConversation = None
    try:
        newConversation = Conversation.CreateWithTemplate(id, userId)
    except NoApiKeyError:
        await CreateConversationWithTemplate.finish("请机器人管理员在设置中添加APIKEY！")
    if newConversation is not None:
        await CreateConversationWithTemplate.send(f"创建{newConversation.name}模板成功!",at_sender=True)
    else :
        await CreateConversationWithTemplate.finish("输入ID无效!")
    if ifGroup:
        if not groupPanels.get(event.group_id):
            groupPanels[event.group_id] = GroupPanel()
        groupPanels[event.group_id].userInConversation[userId] = newConversation
        groupPanels[event.group_id].conversations.append(newConversation)
    else:
        privateConversations[userId] = newConversation


@CreateConversationWithJson.handle()
async def CreateConversation():
    pass


@CreateConversationWithJson.got("jsonStr", "请直接输入json")
async def GetJson(event: Event, jsonStr: str = ArgPlainText("jsonStr")):
    try:
        history = json.loads(jsonStr)
    except:
        logger.error("json文件错误!")
        await CreateConversationWithJson.reject("Json错误!")
    if not history[0].get("role"):
        await CreateConversationWithJson.reject("Json错误!")
    try:
        newConversation = Conversation(history, event.get_user_id())
    except NoApiKeyError:
        await CreateConversationWithJson.finish("请机器人管理员在设置中添加APIKEY！")

    if isinstance(event, GroupMessageEvent):
        groupPanels[event.group_id].conversations.append(newConversation)
        groupPanels[event.group_id].userInConversation[event.get_user_id()
                                                       ] = newConversation
        await CreateConversationWithJson.send("创建对话成功!", at_sender=True)
    elif isinstance(event, PrivateMessageEvent):
        privateConversations[event.get_user_id()] = newConversation
        await CreateConversationWithJson.send("创建对话成功!")
