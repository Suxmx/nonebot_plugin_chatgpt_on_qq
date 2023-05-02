import json
import re
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
    "指令表：\n"
    "    /chat help 获取指令帮助菜单\n"
    "    /talk <会话内容> 在当前会话中进行会话(同样不需要括号，后面直接接你要说的话就行)\n"
    ">> 增\n"
    "    /chat new  根据预制模板prompt创建并加入一个新的会话\n"
    "    /chat new <自定义prompt> 根据自定义prompt创建并加入一个新的会话\n"
    "    /chat json 根据历史会话json来创建一个会话，输入该命令后会提示你在下一个消息中输入json\n"
    "    /chat cp 根据当前会话创建并加入一个新的会话\n"
    "    /chat cp <id> 根据会话<id>为模板进行复制新建加入（id为/chat list中的序号）\n"
    ">> 删\n"
    "    /chat del 删除当前所在会话\n"
    "    /chat del <id> 删除序号为<id>的会话（id为/chat list中的序号）\n"
    "    /chat clear 清空本群全部会话\n"
    "    /chat clear <@user> 删除@用户创建的会话\n"
    ">> 改\n"
    "    /chat join <id> 加入会话（id为/chat list中的序号）\n"
    "    /chat rename <name> 重命名当前会话\n"
    ">> 查\n"
    "    /chat who 查看当前会话信息\n"
    "    /chat list 获取当前群所有存在的会话的序号及创建时间\n"
    "    /chat list <@user> 获取当前群查看@的用户创建的会话\n"
    "    /chat prompt 查看当前会话的prompt\n"
    "    /chat dump 导出当前会话json字符串格式的上下文信息，可以用于/chat json导入\n"

)
__plugin_meta__ = PluginMetadata(
    name="多功能ChatGPT插件",
    description="基于chatGPT-3.5-turbo API的nonebot插件",
    usage=__usage__,
    config=Config,
    extra={
        "License": "BSD License",
        "Author": "颜曦",
        "version": "1.5.0",
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

Chat = on_regex(rf"^{prefix_str}{talk_cmd_str}\s+(?P<content>.+)", flags=re.S, permission=ALLOW_PRIVATE)  # 聊天
CallMenu = on_regex(rf"^{pattern_str}\s+help$", permission=ALLOW_PRIVATE)  # 呼出菜单
ShowList = on_regex(rf"^{pattern_str}\s+list\s*$", permission=ALLOW_PRIVATE)  # 展示群聊天列表
Join = on_regex(rf"^{pattern_str}\s+join\s+(?P<id>\d+)", permission=ALLOW_PRIVATE)  # 加入会话
Delete = on_regex(rf"^{pattern_str}\s+del\s+(?P<id>\d+)", permission=ALLOW_PRIVATE)  # 删除会话
DelSelf = on_regex(rf"^{pattern_str}\s+del\s*$", permission=ALLOW_PRIVATE)  # 删除当前会话
Dump = on_regex(rf"^{pattern_str}\s+dump$", permission=ALLOW_PRIVATE)  # 导出json
CreateConversationWithPrompt = on_regex(rf"^{pattern_str}\s+new\s+(?P<prompt>.+)$", flags=re.S,
                                        permission=ALLOW_PRIVATE)  # 利用自定义prompt创建会话
CreateConversationWithTemplate = on_regex(rf"^{pattern_str}\s+new$", permission=ALLOW_PRIVATE)  # 利用模板创建会话
CreateConversationWithJson = on_regex(rf"^{pattern_str}\s+json$", permission=ALLOW_PRIVATE)  # 利用json创建会话
ChatCopy = on_regex(rf"^{pattern_str}\s+cp\s+(?P<id>\d+)$", permission=ALLOW_PRIVATE)
ChatCP = on_regex(rf"^{pattern_str}\s+cp$", permission=ALLOW_PRIVATE)
ChatWho = on_regex(rf'^{pattern_str}\s+who$', permission=ALLOW_PRIVATE)
ChatUserList = on_regex(rf"^{pattern_str}\s+list\s*\S+$", permission=ALLOW_PRIVATE)  # 展示群聊天列表
ReName = on_regex(rf"^{pattern_str}\s+rename\s+(?P<name>.+)$", permission=ALLOW_PRIVATE)  # 重命名当前会话
ChatPrompt = on_regex(rf"^{pattern_str}\s+prompt$", permission=ALLOW_PRIVATE)
ChatClear = on_regex(rf"{pattern_str}\s+clear$", permission=ALLOW_PRIVATE)
ChatClearAt = on_regex(rf"{pattern_str}\s+clear\s*\S+$", permission=ALLOW_PRIVATE)


@ChatClear.handle()
async def _(bot: Bot, event: MessageEvent):
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if isinstance(event, PrivateMessageEvent):  # 私聊
        session: Session = group_usage.pop(userId)
        if not session:
            await ChatClear.finish("当前不存在会话")
        session_container.sessions.remove(session)
        session.delete_file()
        logger.success(f'成功删除群 {groupId} 会话 {session.name}')
        await ChatClear.finish("已删除当前会话")

    perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
    if not perm_check:
        await ChatClear.finish("只有群主或管理员才能清空本群全部会话!")
    session_list: List[Session] = session_container.get_group_sessions(groupId)
    num = len(session_list)
    for session in session_list:
        await session_container.delete_session(session, groupId)
    await ChatClear.finish(f"成功删除本群全部共{num}条会话")


@ChatClearAt.handle()
async def _(bot: Bot, event: MessageEvent, message: Message = EventMessage()):
    if isinstance(event, PrivateMessageEvent):
        await ChatClearAt.finish()
    segments: List[MessageSegment] = [s for s in message if s.type == 'at' and s.data.get("qq", "all") != 'all']
    if not segments:
        await ChatClearAt.finish()
    perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
    senderId: int = int(event.get_user_id())
    userId: int = int(segments[0].data.get("qq", ""))
    groupId: str = get_group_id(event)
    if userId != senderId and not perm_check:
        await ChatClearAt.finish("您不是该会话的创建者或管理员!")
    session_list: List[Session] = [s for s in session_container.sessions if s.group == groupId and s.creator == userId]
    num = len(session_list)
    if num == 0:
        await ChatClearAt.finish(f"本群用户 {userId} 还没有创建过会话哦")
    for session in session_list:
        await session_container.delete_session(session, groupId)
    await ChatClearAt.finish(f"成功删除本群用户 {userId} 创建的全部会话共{num}条")


@ChatCP.handle()
async def _(event: MessageEvent):
    if isinstance(event, PrivateMessageEvent):
        await ChatCP.finish('私聊中无法复制会话，如果想导出json字符串请使用 /chat dump')
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if userId not in group_usage:
        await ChatCP.finish('请先加入一个会话，再进行复制当前会话 或者使用 /chat cp <id> 进行复制')
    session: Session = group_usage[userId]
    group_usage[userId].del_user(userId)
    new_session: Session = session_container.create_with_session(session, userId, groupId)
    await ChatCP.finish(f"创建并加入会话 '{new_session.name}' 成功!", at_sender=True)


@ChatPrompt.handle()
async def _(event: MessageEvent):
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if userId not in group_usage:
        await ChatPrompt.finish('请先加入一个会话，再进行重命名')
    session: Session = group_usage[userId]
    await ChatPrompt.finish(f'会话：{session.name}\nprompt：{session.prompt}')


@ReName.handle()
async def _(bot: Bot, event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    if isinstance(event, PrivateMessageEvent):
        await ReName.finish('私聊中只存在一个会话，无法命名，如果想导出json字符串请使用 /chat dump')
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if userId not in group_usage:
        await ReName.finish('请先加入一个会话，再进行重命名')
    perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
    session: Session = group_usage[userId]
    name: str = info.get('name', '').strip()
    if session.creator == userId or perm_check:
        session.rename(name[:32])
        await ReName.finish(f'当前会话已命名为 {session.name}')
    logger.info(f'重命名群 {groupId} 会话 {session.name} 失败：权限不足')
    await ReName.finish("您不是该会话的创建者或管理员!")


@ChatUserList.handle()
async def _(event: MessageEvent, message: Message = EventMessage()):
    if isinstance(event, PrivateMessageEvent):
        await ChatUserList.finish('私聊只有一个会话，如果想导出json字符串请使用 /chat dump')
    segments: List[MessageSegment] = [s for s in message if s.type == 'at' and s.data.get("qq", "all") != 'all']
    if not segments:
        await ChatUserList.finish()
    userId: int = int(segments[0].data.get("qq", ""))
    groupId: str = get_group_id(event)
    session_list: List[Session] = [s for s in session_container.sessions if s.group == groupId and s.creator == userId]
    msg: str = f"在群中创建会话{len(session_list)}条：\n"
    for index, session in enumerate(session_list):
        msg += f" 名称:{session.name[:10]} " \
               f"创建者:{session.creator} " \
               f"时间:{datetime.fromtimestamp(session.creation_time)}\n"
    await ChatUserList.finish(MessageSegment.at(userId) + msg)


@ChatWho.handle()
async def _(event: MessageEvent):
    if isinstance(event, PrivateMessageEvent):
        await ChatWho.finish('私聊只有一个会话，如果想导出json字符串请使用 /chat dump')
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if userId not in group_usage:
        await ChatWho.finish('当前没有加入任何会话，请加入或创建一个会话')
    session: Session = group_usage[userId]
    msg = f'当前所在会话信息:\n' \
          f"名称:{session.name[:10]}\n" \
          f"创建者:{session.creator}\n" \
          f"时间:{datetime.fromtimestamp(session.creation_time)}\n" \
          f"可以使用 /chat dump 导出json字符串格式的上下文信息"
    await ChatWho.finish(msg)


@ChatCopy.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    if isinstance(event, PrivateMessageEvent):
        await ChatCopy.finish('私聊中无法复制会话，如果想导出json字符串请使用 /chat dump')
    session_id = int(info.get('id', '').strip())
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_sessions: List[Session] = session_container.get_group_sessions(groupId)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if not group_sessions:
        await ChatCopy.finish("本群尚未创建过会话!请用/chat new命令来创建会话!", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await ChatCopy.finish("序号超出!", at_sender=True)
    session: Session = group_sessions[session_id - 1]
    if userId in group_usage:
        group_usage[userId].del_user(userId)
    new_session: Session = session_container.create_with_session(session, userId, groupId)
    await ChatCopy.finish(f"创建并加入会话 '{new_session.name}' 成功!", at_sender=True)


@Dump.handle()
async def _(event: MessageEvent):
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    try:
        session: Session = session_container.get_user_usage(groupId, userId)
        await Dump.finish(session.dump2json_str())
    except NeedCreatSession:
        await Dump.finish('请先加入一个会话')


@Chat.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    content: str = info.get('content', '').strip()
    if not content:
        await Chat.finish("输入不能为空!", at_sender=True)
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if userId not in group_usage:  # 若用户没有加入任何会话则先创建会话
        session: Session = session_container.create_with_template('1', userId, groupId)
        logger.info(f"{userId} 自动创建并加入会话 '{session.name}'")
        if auto_create_preset_info:
            await Chat.send(f"自动创建并加入会话 '{session.name}' 成功", at_sender=True)
    else:
        session: Session = group_usage[userId]
    answer: str = await session.ask_with_content(api_keys, content, 'user', temperature, model, max_tokens)
    if answer:
        await Chat.finish(answer)
    await Chat.finish('连接失败...报错信息请查看日志')


@Join.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    if isinstance(event, PrivateMessageEvent):
        await Join.finish("私聊中无法加入会话!")
    session_id: int = int(info.get('id', '').strip())
    groupId: str = get_group_id(event)
    group_sessions: List[Session] = session_container.get_group_sessions(groupId)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if not group_sessions:
        await Join.finish("本群尚未创建过会话!请用/chat new命令来创建会话!", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await Join.finish("序号超出!", at_sender=True)
    userId: int = int(event.get_user_id())
    session: Session = group_sessions[session_id - 1]
    if userId in group_usage:
        group_usage[userId].del_user(userId)
    session.add_user(userId)
    group_usage[userId] = session
    await Join.finish(f"加入会话 {session_id}:{session.name} 成功!", at_sender=True)


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
        await DelSelf.finish("当前不存在会话")
    if isinstance(event, PrivateMessageEvent):  # 私聊
        session_container.sessions.remove(session)
        session.delete_file()
        logger.success(f'成功删除群 {groupId} 会话 {session.name}')
        await DelSelf.finish("已删除当前会话")
    perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
    if session.creator == userId or perm_check:
        await session_container.delete_session(session, groupId)
        await DelSelf.finish("删除成功!")
    logger.info(f'删除群 {groupId} 会话 {session.name} 失败：权限不足')
    await DelSelf.finish("您不是该会话的创建者或管理员!")


@Delete.handle()
async def _(bot: Bot, event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    session_id = int(info.get('id', '').strip())
    userId: int = int(event.get_user_id())
    groupId: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(groupId)
    if isinstance(event, PrivateMessageEvent):  # 私聊
        session: Session = group_usage.pop(userId)
        if not session:
            await Delete.finish("当前不存在会话")
        session_container.sessions.remove(session)
        session.delete_file()
        logger.success(f'成功删除群 {groupId} 会话 {session.name}')
        await Delete.finish("已删除当前会话")
    # 群聊
    group_sessions: List[Session] = session_container.get_group_sessions(groupId)
    if not group_sessions:
        await Delete.finish("本群尚未创建过会话!", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await Delete.finish("序号超出!", at_sender=True)
    perm_check = (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))
    session: Session = group_sessions[session_id - 1]
    if session.creator == userId or perm_check:
        await session_container.delete_session(session, groupId)
        await Delete.finish("删除成功!")
    else:
        logger.info(f'删除群 {groupId} 会话 {session.name} 失败：权限不足')
        await Delete.finish("您不是该会话的创建者或管理员!")


# 暂时已完成


@ShowList.handle()
async def _(event: MessageEvent):
    if isinstance(event, PrivateMessageEvent):
        await ShowList.finish("私聊中无法展示列表(最多只有一个会话)，如果想导出json字符串请使用 /chat dump")
    groupId: str = get_group_id(event)
    session_list: List[Session] = session_container.get_group_sessions(groupId)
    msg: str = f"本群全部会话共{len(session_list)}条：\n"
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
            await CreateConversationWithPrompt.finish("已存在一个会话,请先删除")
    session: Session = session_container.create_with_str(customPrompt, userId, groupId, customPrompt[:5])
    await CreateConversationWithPrompt.finish(f"成功创建并加入会话 '{session.name}' ", at_sender=True)


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
            await CreateConversationWithPrompt.finish("已存在一个会话，请先删除该会话!")
    if not template_id.isdigit():
        await CreateConversationWithTemplate.reject("输入ID无效!")
    session: Session = session_container.create_with_template(template_id, userId, groupId)
    await CreateConversationWithTemplate.send(f"使用模板 '{template_id}' 创建并加入会话 '{session.name}' 成功!",
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
    await CreateConversationWithJson.send(f"创建并加入会话 '{session}' 成功!", at_sender=True)
