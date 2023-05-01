import json
from datetime import datetime
from json import JSONDecodeError
from typing import Dict, List, Any

from nonebot.adapters.onebot.v11 import (Bot, MessageEvent,
                                         GroupMessageEvent, PrivateMessageEvent,
                                         GROUP_ADMIN, GROUP_OWNER, MessageSegment, Message)
from nonebot.log import logger
from nonebot.plugin import on_regex
from nonebot.params import ArgPlainText, RegexDict, EventMessage
from nonebot.permission import SUPERUSER, Permission
from nonebot.plugin import PluginMetadata

from .config import Config, plugin_config
from .loadpresets import presets_str
from .custom_errors import NeedCreatSession
from .sessions import session_container, Session, get_group_id

__usage__: str = (
        "太长不看版:\n"
        + "先用/chat new命令,选择模板来创建对话,随后/talk 内容 来对话\n\n"
        + "/chat :获取菜单\n"
        + "/chat new :利用模板创建一个对话并加入\n"
        + "/talk <内容> :在当前的对话进行聊天\n"
        + "/chat list :获得当前已创建的对话列表\n"
        + "/chat list <@user> :查看@的用户创建的对话\n"
        + "/chat join 序号(指/chat list中的序号) :参与list中的某个对话\n"
        + "/chat new (prompt) :自定义prompt来创建一个新的对话\n"
        + "/chat del :删除当前所在对话\n"
        + "/chat del 序号(指/chat list中的序号) :删除list中的某个对话\n"
        + "/chat dump :导出当前对话json字符串格式的上下文信息\n"
        + "/chat cp <chat id> :复制对话并新建\n"
        + "/chat who :查看当前对话\n"
)
__plugin_meta__ = PluginMetadata(
    name="多功能ChatGPT插件",
    description="基于chatGPT-3.5-turbo API的nonebot插件",
    usage=__usage__,
    config=Config,
    extra={
        "License": "BSD License",
        "Author": "颜曦",
        "version": "1.4.0",
    },
)

allow_private: bool = plugin_config.allow_private
api_keys: List[str] = session_container.api_keys
temperature: float = plugin_config.temperature
model: str = plugin_config.model_name
max_tokens: int = plugin_config.max_tokens
auto_create_preset_info: bool = plugin_config.auto_create_preset_info
customize_prefix: str = plugin_config.customize_prefix
customize_talk_cmd: str = plugin_config.customize_talk_cmd

# 因为电脑端的qq在输入/chat xxx时候经常被转换成表情，所以支持自定义指令前缀替换"chat"
change_chat_to: str = plugin_config.change_chat_to
prefix_str = customize_prefix if customize_prefix is not None else '/'
chat_str = f'(chat|{change_chat_to})' if change_chat_to else 'chat'
talk_cmd_str = customize_talk_cmd if customize_talk_cmd else 'talk'
pattern_str = prefix_str + chat_str


async def _allow_private_checker(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) or allow_private


ALLOW_PRIVATE = Permission(_allow_private_checker)

Chat = on_regex(rf"^{prefix_str}{talk_cmd_str}\s+(?P<content>.+)", permission=ALLOW_PRIVATE)  # 聊天
CallMenu = on_regex(rf"^{pattern_str}$", permission=ALLOW_PRIVATE)  # 呼出菜单
ShowList = on_regex(rf"^{pattern_str}\s+list\s*$", permission=ALLOW_PRIVATE)  # 展示群聊天列表
Join = on_regex(rf"^{pattern_str}\s+join\s+(?P<id>\d+)", permission=ALLOW_PRIVATE)  # 加入对话
Delete = on_regex(rf"^{pattern_str}\s+del\s+(?P<id>\d+)", permission=ALLOW_PRIVATE)  # 删除对话
DelSelf = on_regex(rf"^{pattern_str}\s+del\s*$", permission=ALLOW_PRIVATE)  # 删除当前对话
Dump = on_regex(rf"^{pattern_str}\s+dump$", permission=ALLOW_PRIVATE)  # 导出json
CreateConversationWithPrompt = on_regex(rf"^{pattern_str}\s+new\s+(?P<prompt>.+)$",
                                        permission=ALLOW_PRIVATE)  # 利用自定义prompt创建对话
CreateConversationWithTemplate = on_regex(rf"^{pattern_str}\s+new$", permission=ALLOW_PRIVATE)  # 利用模板创建对话
CreateConversationWithJson = on_regex(rf"^{pattern_str}\s+json$", permission=ALLOW_PRIVATE)  # 利用json创建对话
ChatCopy = on_regex(rf"^{pattern_str}\s+cp\s+(?P<id>\d+)$", permission=ALLOW_PRIVATE)
ChatWho = on_regex(rf'^{pattern_str}\s+who$', permission=ALLOW_PRIVATE)
ChatUserList = on_regex(rf"^{pattern_str}\s+list\s*\S+$", permission=ALLOW_PRIVATE)  # 展示群聊天列表


@ChatUserList.handle()
async def _(event: MessageEvent, message: Message = EventMessage()):
    if isinstance(event, PrivateMessageEvent):
        await ChatUserList.finish('私聊只有一个对话，如果想导出json字符串请使用 /chat dump')
    segments: List[MessageSegment] = [s for s in message if s.type == 'at' and s.data.get("qq", "all") != 'all']
    if not segments:
        await ChatUserList.finish()
    userId: int = int(segments[0].data.get("qq", ""))
    groupId: str = get_group_id(event)
    session_list: List[Session] = [s for s in session_container.sessions if s.group == groupId and s.creator == userId]
    msg: str = f"在群中创建对话{len(session_list)}条：\n"
    for index, session in enumerate(session_list):
        msg += f" 名称:{session.name} " \
               f"创建者:{session.creator} " \
               f"时间:{datetime.fromtimestamp(session.creation_time)}\n"
    await ChatUserList.finish(MessageSegment.at(userId) + msg)


@ChatWho.handle()
async def _(event: MessageEvent):
    if isinstance(event, PrivateMessageEvent):
        await ChatWho.finish('私聊只有一个对话，如果想导出json字符串请使用 /chat dump')
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if userId not in group_usage:
        await ChatWho.finish('当前没有加入任何对话，请加入或创建一个对话')
    session: Session = group_usage[userId]
    msg = f'当前所在对话信息:\n' \
          f"名称:{session.name}\n" \
          f"创建者:{session.creator}\n" \
          f"时间:{datetime.fromtimestamp(session.creation_time)}\n" \
          f"可以使用 /chat dump 导出json字符串格式的上下文信息"
    await ChatWho.finish(msg)


@ChatCopy.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    if isinstance(event, PrivateMessageEvent):
        await ChatCopy.finish('私聊中无法复制对话，如果想导出json字符串请使用 /chat dump')
    session_id = int(info.get('id', '').strip())
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_sessions: List[Session] = session_container.get_group_sessions(groupId)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if not group_sessions:
        await Join.finish("本群尚未创建过对话!请用/chat new命令来创建对话!", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await Join.finish("序号超出!", at_sender=True)
    session: Session = group_sessions[session_id - 1]
    if userId in group_usage:
        group_usage[userId].del_user(userId)
    new_session: Session = session_container.create_with_session(session, userId, groupId)
    await Join.finish(f"创建并加入对话 '{new_session.name}' 成功!", at_sender=True)


@Dump.handle()
async def _(event: MessageEvent):
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    try:
        session: Session = session_container.get_user_usage(groupId, userId)
        await Dump.finish(session.dump2json_str())
    except NeedCreatSession:
        await Dump.finish('请先加入一个对话')


@Chat.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    content: str = info.get('content', '').strip()
    if not content:
        await Chat.finish("输入不能为空!", at_sender=True)
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if userId not in group_usage:  # 若用户没有加入任何对话则先创建对话
        session: Session = session_container.create_with_template('1', userId, groupId)
        logger.info(f"{userId} 自动创建并加入对话 '{session.name}'")
        if auto_create_preset_info:
            await Chat.send(f"自动创建并加入对话 '{session.name}' 成功", at_sender=True)
    else:
        session: Session = group_usage[userId]
    answer: str = await session.ask_with_content(api_keys, content, 'user', temperature, model, max_tokens)
    if answer:
        await Chat.finish(answer)
    await Chat.finish('连接失败...报错信息请查看日志')


@Join.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    if isinstance(event, PrivateMessageEvent):
        await Join.finish("私聊中无法加入对话!")
    session_id: int = int(info.get('id', '').strip())
    groupId: str = get_group_id(event)
    group_sessions: List[Session] = session_container.get_group_sessions(groupId)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if not group_sessions:
        await Join.finish("本群尚未创建过对话!请用/chat new命令来创建对话!", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await Join.finish("序号超出!", at_sender=True)
    userId: int = int(event.get_user_id())
    session: Session = group_sessions[session_id - 1]
    if userId in group_usage:
        group_usage[userId].del_user(userId)
    session.add_user(userId)
    group_usage[userId] = session
    await Join.finish(f"加入对话 {session_id}:{session.name} 成功!", at_sender=True)


@CallMenu.handle()
async def _():
    menu: str = __usage__
    await CallMenu.finish(menu, at_sender=True)


@DelSelf.handle()
async def _(bot: Bot, event: MessageEvent):
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    session: Session = group_usage.pop(userId)
    if not session:
        await Delete.finish("当前不存在对话")
    if isinstance(event, PrivateMessageEvent):  # 私聊
        session_container.sessions.remove(session)
        session.delete_file()
        logger.success(f'成功删除群 {groupId} 对话 {session.name}')
        await Delete.finish("已删除当前对话")
    perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
    if session.creator == userId or perm_check:
        users = set(uid for uid, s in group_usage.items() if s is session)
        for user in users:
            group_usage.pop(user)
        session_container.sessions.remove(session)
        session.delete_file()
        logger.success(f'成功删除群 {groupId} 对话 {session.name}')
        await Delete.finish("删除成功!")
    logger.info(f'删除群 {groupId} 对话 {session.name} 失败：权限不足')
    await Delete.finish("您不是该对话的创建者或管理员!")


@Delete.handle()
async def _(bot: Bot, event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    session_id = int(info.get('id', '').strip())
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if isinstance(event, PrivateMessageEvent):  # 私聊
        session: Session = group_usage.pop(userId)
        if not session:
            await Delete.finish("当前不存在对话")
        session_container.sessions.remove(session)
        session.delete_file()
        logger.success(f'成功删除群 {groupId} 对话 {session.name}')
        await Delete.finish("已删除当前对话")
    # 群聊
    group_sessions: List[Session] = session_container.get_group_sessions(groupId)
    if not group_sessions:
        await Join.finish("本群尚未创建过对话!", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await Join.finish("序号超出!", at_sender=True)
    perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
    session: Session = group_sessions[session_id - 1]
    if session.creator == userId or perm_check:
        users = set(uid for uid, s in group_usage.items() if s is session)
        for user in users:
            group_usage.pop(user)
        session_container.sessions.remove(session)
        session.delete_file()
        logger.success(f'成功删除群 {groupId} 对话 {session.name}')
        await Delete.finish("删除成功!")
    else:
        logger.info(f'删除群 {groupId} 对话 {session.name} 失败：权限不足')
        await Delete.finish("您不是该对话的创建者或管理员!")


# 暂时已完成


@ShowList.handle()
async def _(event: MessageEvent):
    if isinstance(event, PrivateMessageEvent):
        await ShowList.finish("私聊中无法展示列表(最多只有一个对话)，如果想导出json字符串请使用 /chat dump")
    groupId: str = get_group_id(event)
    session_list: List[Session] = session_container.get_group_sessions(groupId)
    msg: str = f"本群全部对话共{len(session_list)}条：\n"
    for index, session in enumerate(session_list):
        msg += f"{index + 1}. {session.name} " \
               f"创建者:{session.creator} " \
               f"时间:{datetime.fromtimestamp(session.creation_time)}\n"
    await ShowList.finish(msg, at_sender=True)


# 暂时完成


@CreateConversationWithPrompt.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    customPrompt: str = info.get('prompt', '').strip()
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    if isinstance(event, PrivateMessageEvent):  # 当在私聊中时
        if userId in session_container.get_group_usage(groupId):
            await CreateConversationWithPrompt.finish("已存在一个对话,请先删除")
    session: Session = session_container.create_with_str(customPrompt, userId, groupId, customPrompt[:5])
    await CreateConversationWithPrompt.finish(f"成功创建并加入对话 '{session.name}' ", at_sender=True)


@CreateConversationWithTemplate.handle()
async def CreateConversation():
    await CreateConversationWithTemplate.send(presets_str, at_sender=True)


# 暂时完成


@CreateConversationWithTemplate.got(key="template")
async def Create(event: MessageEvent, template_id: str = ArgPlainText("template")):
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    if isinstance(event, PrivateMessageEvent):  # 当在私聊中时
        if userId in session_container.get_group_usage(groupId):
            await CreateConversationWithPrompt.finish("已存在一个对话，请先删除该对话!")
    if not template_id.isdigit():
        await CreateConversationWithTemplate.reject("输入ID无效!")
    session: Session = session_container.create_with_template(template_id, userId, groupId)
    await CreateConversationWithTemplate.send(f"使用模板 '{template_id}' 创建并加入对话 '{session.name}' 成功!",
                                              at_sender=True)


@CreateConversationWithJson.handle()
async def CreateConversation():
    pass


@CreateConversationWithJson.got("jsonStr", "请直接输入json")
async def GetJson(event: MessageEvent, json_str: str = ArgPlainText("jsonStr")):
    try:
        chat_log = json.loads(json_str)
    except JSONDecodeError:
        logger.error("json字符串错误!")
        await CreateConversationWithJson.reject("Json错误!")
    if not chat_log[0].get("role"):
        await CreateConversationWithJson.reject("Json错误!")
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    session: Session = session_container.create_with_chat_log(chat_log, userId, groupId,
                                                              name=chat_log[0].get('content', '')[:5])
    await CreateConversationWithJson.send(f"创建并加入对话 '{session}' 成功!", at_sender=True)
