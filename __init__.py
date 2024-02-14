import re
import json
from datetime import datetime
from json import JSONDecodeError
from typing import Dict, List, Any, Type

from nonebot.adapters.onebot.v11.utils import unescape
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11 import (Bot, MessageEvent,
                                         GroupMessageEvent, PrivateMessageEvent,
                                         GROUP_ADMIN, GROUP_OWNER, MessageSegment, Message)
from nonebot.internal.matcher import Matcher
from nonebot.log import logger
from nonebot.plugin import on_regex
from nonebot.params import ArgPlainText, RegexDict, EventMessage
from nonebot.permission import SUPERUSER, Permission
from nonebot.plugin import PluginMetadata

from .config import Config, plugin_config, APIKeyPool
from .loadpresets import presets_str
from .custom_errors import NeedCreatSession
from .sessions import session_container, Session, get_group_id

customize_prefix: str = plugin_config.customize_prefix
customize_talk_cmd: str = plugin_config.customize_talk_cmd
# 因为电脑端的qq在输入/chat xxx时候经常被转换成表情，所以支持自定义指令前缀替换"chat"
change_chat_to: str = plugin_config.change_chat_to
prefix_str = customize_prefix if customize_prefix is not None else '/'
chat_str = f'(chat|{change_chat_to})' if change_chat_to else 'chat'
talk_cmd_str = customize_talk_cmd if customize_talk_cmd else 'talk'
pattern_str = prefix_str + chat_str
menu_chat_str = prefix_str + f'{change_chat_to}' if change_chat_to else 'chat'

__usage__: str = (
    "指令表：\n"
    f"    {menu_chat_str} help 获取指令帮助菜单\n"
    f"    {menu_chat_str} auth 获取当前群会话管理权限状态\n"
    f"    {menu_chat_str} auth on 设置当前群仅管理员可以管理会话\n"
    f"    {menu_chat_str} auth off 设置当前群所有人均可管理会话\n"
    f"    {prefix_str}{talk_cmd_str} <会话内容> 在当前会话中进行会话(同样不需要括号，后面直接接你要说的话就行)\n"
    ">> 增\n"
    f"    {menu_chat_str} new  根据预制模板prompt创建并加入一个新的会话\n"
    f"    {menu_chat_str} new <自定义prompt> 根据自定义prompt创建并加入一个新的会话\n"
    f"    {menu_chat_str} json 根据历史会话json来创建一个会话，输入该命令后会提示你在下一个消息中输入json\n"
    f"    {menu_chat_str} cp 根据当前会话创建并加入一个新的会话\n"
    f"    {menu_chat_str} cp <id> 根据会话<id>为模板进行复制新建加入（id为{menu_chat_str} list中的序号）\n"
    ">> 删\n"
    f"    {menu_chat_str} del 删除当前所在会话\n"
    f"    {menu_chat_str} del <id> 删除序号为<id>的会话（id为{menu_chat_str} list中的序号）\n"
    f"    {menu_chat_str} clear 清空本群全部会话\n"
    f"    {menu_chat_str} clear <@user> 删除@用户创建的会话\n"
    ">> 改\n"
    f"    {menu_chat_str} join <id> 加入会话（id为{menu_chat_str} list中的序号）\n"
    f"    {menu_chat_str} rename <name> 重命名当前会话\n"
    ">> 查\n"
    f"    {menu_chat_str} who 查看当前会话信息\n"
    f"    {menu_chat_str} list 获取当前群所有存在的会话的序号及创建时间\n"
    f"    {menu_chat_str} list <@user> 获取当前群查看@的用户创建的会话\n"
    f"    {menu_chat_str} prompt 查看当前会话的prompt\n"
    f"    {menu_chat_str} dump 导出当前会话json字符串格式的上下文信息，可以用于{menu_chat_str} json导入\n"
    f"    {menu_chat_str} keys 脱敏显示当前失效api key，仅主人"

)
__plugin_meta__ = PluginMetadata(
    name="多功能ChatGPT插件",
    description="基于chatGPT-3.5-turbo API的nonebot插件",
    usage=__usage__,
    config=Config,
    extra={
        "License": "BSD License",
        "Author": "颜曦",
        "version": "1.6.1",
    },
)

allow_private: bool = plugin_config.allow_private
api_keys: APIKeyPool = session_container.api_keys
base_url: str = session_container.base_url
temperature: float = plugin_config.temperature
model: str = plugin_config.model_name
max_tokens: int = plugin_config.max_tokens
auto_create_preset_info: bool = plugin_config.auto_create_preset_info
at_sender: bool = plugin_config.at_sender


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
SetAuthOn = on_regex(rf'^{pattern_str}\s+auth on$', permission=GROUP)
SetAuthOff = on_regex(rf'^{pattern_str}\s+auth off$', permission=GROUP)
ShowAuth = on_regex(rf'^{pattern_str}\s+auth$', permission=GROUP)
ShowFailKey = on_regex(rf'^{pattern_str}\s+keys$', permission=SUPERUSER)


@ShowFailKey.handle()
async def _(event: MessageEvent):
    await ShowFailKey.finish(api_keys.show_fail_keys(), at_sender=True)


@ShowAuth.handle()
async def _(event: GroupMessageEvent):
    group_id: str = get_group_id(event)
    if session_container.get_group_auth(group_id):
        await ShowAuth.finish("当前仅有管理员有权限管理会话", at_sender=True)
    await ShowAuth.finish("当前所有人均有权限管理会话", at_sender=True)


async def auth_check(matcher: Type[Matcher], bot: Bot, event: MessageEvent, group_id: str) -> None:
    if isinstance(event, PrivateMessageEvent):
        return
    if session_container.get_group_auth(group_id) and not (await admin_check(bot, event)):
        await matcher.finish('该群仅有管理员可以管理会话', at_sender=True)


async def admin_check(bot: Bot, event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return True
    return (await SUPERUSER(bot, event)) or (await GROUP_ADMIN(bot, event)) or (await GROUP_OWNER(bot, event))


@SetAuthOff.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id: str = get_group_id(event)
    perm_check = await admin_check(bot, event)
    if not perm_check:
        await SetAuthOff.finish("只有群主或管理员才能设置权限管理", at_sender=True)
    session_container.set_group_auth(group_id, False)
    await SetAuthOff.finish("设置成功，当前所有人均有权限管理会话", at_sender=True)


@SetAuthOn.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id: str = get_group_id(event)
    perm_check = await admin_check(bot, event)
    if not perm_check:
        await SetAuthOn.finish("只有群主或管理员才能设置权限管理", at_sender=True)
    session_container.set_group_auth(group_id, True)
    await SetAuthOn.finish("设置成功，当前仅有管理员有权限管理会话", at_sender=True)


@ChatClear.handle()
async def _(bot: Bot, event: MessageEvent):
    group_id: str = get_group_id(event)
    perm_check = await admin_check(bot, event)
    if not perm_check:
        await ChatClear.finish("只有群主或管理员才能清空本群全部会话!", at_sender=True)
    session_list: List[Session] = session_container.get_group_sessions(group_id)
    num = len(session_list)
    for session in session_list:
        await session_container.delete_session(session, group_id)
    await ChatClear.finish(f"成功删除全部共{num}条会话", at_sender=True)


@ChatClearAt.handle()
async def _(bot: Bot, event: MessageEvent, message: Message = EventMessage()):
    if isinstance(event, PrivateMessageEvent):
        await ChatClearAt.finish()
    segments: List[MessageSegment] = [s for s in message if s.type == 'at' and s.data.get("qq", "all") != 'all']
    if not segments:
        await ChatClearAt.finish()
    perm_check = await admin_check(bot, event)
    sender_id: int = int(event.get_user_id())
    user_id: int = int(segments[0].data.get("qq", ""))
    group_id: str = get_group_id(event)
    if user_id != sender_id and not perm_check:
        await ChatClearAt.finish("您不是该会话的创建者或管理员!", at_sender=True)
    session_list: List[Session] = [s for s in session_container.sessions if
                                   s.group == group_id and s.creator == user_id]
    num = len(session_list)
    if num == 0:
        await ChatClearAt.finish(f"本群用户 {user_id} 还没有创建过会话哦", at_sender=True)
    for session in session_list:
        await session_container.delete_session(session, group_id)
    await ChatClearAt.finish(f"成功删除本群用户 {user_id} 创建的全部会话共{num}条", at_sender=True)


@ChatCP.handle()
async def _(bot: Bot, event: MessageEvent):
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    await auth_check(ChatCP, bot, event, group_id)
    group_usage: Dict[int, Session] = session_container.get_group_usage(group_id)
    if user_id not in group_usage:
        await ChatCP.finish(f'请先加入一个会话，再进行复制当前会话 或者使用 {menu_chat_str} cp <id> 进行复制',
                            at_sender=True)
    session: Session = group_usage[user_id]
    group_usage[user_id].del_user(user_id)
    new_session: Session = session_container.create_with_session(session, user_id, group_id)
    await ChatCP.finish(f"创建并加入会话 '{new_session.name}' 成功!", at_sender=True)


@ChatPrompt.handle()
async def _(event: MessageEvent):
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(group_id)
    if user_id not in group_usage:
        await ChatPrompt.finish('请先加入一个会话，再进行重命名', at_sender=True)
    session: Session = group_usage[user_id]
    await ChatPrompt.finish(f'会话：{session.name}\nprompt：{session.prompt}', at_sender=True)


@ReName.handle()
async def _(bot: Bot, event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    await auth_check(ReName, bot, event, group_id)
    group_usage: Dict[int, Session] = session_container.get_group_usage(group_id)
    if user_id not in group_usage:
        await ReName.finish('请先加入一个会话，再进行重命名', at_sender=True)
    perm_check = await admin_check(bot, event)
    session: Session = group_usage[user_id]
    name: str = unescape(info.get('name', '').strip())
    if session.creator == user_id or perm_check:
        session.rename(name[:32])
        await ReName.finish(f'当前会话已命名为 {session.name}', at_sender=True)
    logger.info(f'重命名群 {group_id} 会话 {session.name} 失败：权限不足', at_sender=True)
    await ReName.finish("您不是该会话的创建者或管理员!", at_sender=True)


@ChatUserList.handle()
async def _(event: MessageEvent, message: Message = EventMessage()):
    if isinstance(event, PrivateMessageEvent):
        await ChatUserList.finish()
    segments: List[MessageSegment] = [s for s in message if s.type == 'at' and s.data.get("qq", "all") != 'all']
    if not segments:
        await ChatUserList.finish()
    user_id: int = int(segments[0].data.get("qq", ""))
    group_id: str = get_group_id(event)
    session_list: List[Session] = [s for s in session_container.sessions if
                                   s.group == group_id and s.creator == user_id]
    msg: str = f"在群中创建会话{len(session_list)}条：\n"
    for index, session in enumerate(session_list):
        msg += f" 名称:{session.name[:10]} " \
               f"创建者:{session.creator} " \
               f"时间:{datetime.fromtimestamp(session.creation_time)}\n"
    await ChatUserList.finish(MessageSegment.at(user_id) + msg, at_sender=True)


@ChatWho.handle()
async def _(event: MessageEvent):
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(group_id)
    if user_id not in group_usage:
        await ChatWho.finish('当前没有加入任何会话，请加入或创建一个会话', at_sender=True)
    session: Session = group_usage[user_id]
    msg = f'当前所在会话信息:\n' \
          f"名称:{session.name[:10]}\n" \
          f"创建者:{session.creator}\n" \
          f"时间:{datetime.fromtimestamp(session.creation_time)}\n" \
          f"可以使用 {menu_chat_str} dump 导出json字符串格式的上下文信息"
    await ChatWho.finish(msg, at_sender=True)


@ChatCopy.handle()
async def _(bot: Bot, event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    session_id = int(info.get('id', '').strip())
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    await auth_check(ChatCopy, bot, event, group_id)
    group_sessions: List[Session] = session_container.get_group_sessions(group_id)
    group_usage: Dict[int, Session] = session_container.get_group_usage(group_id)
    if not group_sessions:
        await ChatCopy.finish(f"本群尚未创建过会话!请用{menu_chat_str} new命令来创建会话!", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await ChatCopy.finish("序号超出!", at_sender=True)
    session: Session = group_sessions[session_id - 1]
    if user_id in group_usage:
        group_usage[user_id].del_user(user_id)
    new_session: Session = session_container.create_with_session(session, user_id, group_id)
    await ChatCopy.finish(f"创建并加入会话 '{new_session.name}' 成功!", at_sender=True)


@Dump.handle()
async def _(event: MessageEvent):
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    try:
        session: Session = session_container.get_user_usage(group_id, user_id)
        await Dump.finish(session.dump2json_str(), at_sender=True)
    except NeedCreatSession:
        await Dump.finish('请先加入一个会话', at_sender=True)


@Chat.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    content: str = unescape(info.get('content', '').strip())
    if not content:
        await Chat.finish("输入不能为空!", at_sender=True)
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    group_usage: Dict[int, Session] = session_container.get_group_usage(group_id)
    if user_id not in group_usage:  # 若用户没有加入任何会话则先创建会话
        session: Session = session_container.create_with_template('1', user_id, group_id)
        logger.info(f"{user_id} 自动创建并加入会话 '{session.name}'")
        if auto_create_preset_info:
            await Chat.send(f"自动创建并加入会话 '{session.name}' 成功", at_sender=True)
    else:
        session: Session = group_usage[user_id]
    answer: str = await session.ask_with_content(api_keys, base_url ,content, 'user', temperature, model, max_tokens)
    await Chat.finish(answer, at_sender=at_sender)


@Join.handle()
async def _(event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    session_id: int = int(info.get('id', '').strip())
    group_id: str = get_group_id(event)
    group_sessions: List[Session] = session_container.get_group_sessions(group_id)
    group_usage: Dict[int, Session] = session_container.get_group_usage(group_id)
    if not group_sessions:
        await Join.finish(f"本群尚未创建过会话!请用{menu_chat_str} new命令来创建会话!", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await Join.finish("序号超出!", at_sender=True)
    user_id: int = int(event.get_user_id())
    session: Session = group_sessions[session_id - 1]
    if user_id in group_usage:
        group_usage[user_id].del_user(user_id)
    session.add_user(user_id)
    group_usage[user_id] = session
    await Join.finish(f"加入会话 {session_id}:{session.name} 成功!", at_sender=True)


@CallMenu.handle()
async def _():
    menu: str = __usage__
    await CallMenu.finish(menu, at_sender=True)


@DelSelf.handle()
async def _(bot: Bot, event: MessageEvent):
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    await auth_check(DelSelf, bot, event, group_id)
    group_usage: Dict[int, Session] = session_container.get_group_usage(group_id)
    session: Session = group_usage.pop(user_id, None)
    if not session:
        await DelSelf.finish("当前不存在会话", at_sender=True)
    perm_check = await admin_check(bot, event)
    if session.creator == user_id or perm_check:
        await session_container.delete_session(session, group_id)
        await DelSelf.finish("删除成功!", at_sender=True)
    logger.info(f'删除群 {group_id} 会话 {session.name} 失败：权限不足', at_sender=True)
    await DelSelf.finish("您不是该会话的创建者或管理员!", at_sender=True)


@Delete.handle()
async def _(bot: Bot, event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    session_id = int(info.get('id', '').strip())
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    await auth_check(Delete, bot, event, group_id)
    group_sessions: List[Session] = session_container.get_group_sessions(group_id)
    if not group_sessions:
        await Delete.finish("当前不存在会话", at_sender=True)
    if session_id < 1 or session_id > len(group_sessions):
        await Delete.finish("序号超出!", at_sender=True)
    session: Session = group_sessions[session_id - 1]
    perm_check = await admin_check(bot, event)
    if session.creator == user_id or perm_check:
        await session_container.delete_session(session, group_id)
        await Delete.finish("删除成功!", at_sender=True)
    else:
        logger.info(f'删除群 {group_id} 会话 {session.name} 失败：权限不足', at_sender=True)
        await Delete.finish("您不是该会话的创建者或管理员!", at_sender=True)


# 暂时已完成


@ShowList.handle()
async def _(event: MessageEvent):
    group_id: str = get_group_id(event)
    session_list: List[Session] = session_container.get_group_sessions(group_id)
    msg: str = f"本群全部会话共{len(session_list)}条：\n"
    for index, session in enumerate(session_list):
        msg += f"{index + 1}. {session.name} " \
               f"创建者:{session.creator} " \
               f"时间:{datetime.fromtimestamp(session.creation_time)}\n"
    await ShowList.finish(msg, at_sender=True)


# 暂时完成


@CreateConversationWithPrompt.handle()
async def _(bot: Bot, event: MessageEvent, info: Dict[str, Any] = RegexDict()):
    custom_prompt: str = unescape(info.get('prompt', '').strip())
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    await auth_check(CreateConversationWithPrompt, bot, event, group_id)
    session: Session = session_container.create_with_str(custom_prompt, user_id, group_id, custom_prompt[:5])
    await CreateConversationWithPrompt.finish(f"成功创建并加入会话 '{session.name}' ", at_sender=True)


@CreateConversationWithTemplate.handle()
async def CreateConversation(bot: Bot, event: MessageEvent):
    group_id: str = get_group_id(event)
    await auth_check(CreateConversationWithTemplate, bot, event, group_id)
    await CreateConversationWithTemplate.send(presets_str, at_sender=True)


# 暂时完成


@CreateConversationWithTemplate.got(key="template")
async def Create(event: MessageEvent, template_id: str = ArgPlainText("template")):
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    if not template_id.isdigit():
        await CreateConversationWithTemplate.finish("输入ID无效！", at_sender=True)
    session: Session = session_container.create_with_template(template_id, user_id, group_id)
    await CreateConversationWithTemplate.send(f"使用模板 '{template_id}' 创建并加入会话 '{session.name}' 成功!",
                                              at_sender=True)


@CreateConversationWithJson.handle()
async def CreateConversation(bot: Bot, event: MessageEvent):
    group_id: str = get_group_id(event)
    await auth_check(CreateConversationWithTemplate, bot, event, group_id)
    pass


@CreateConversationWithJson.got("jsonStr", "请直接输入json")
async def GetJson(event: MessageEvent, json_str: str = ArgPlainText("jsonStr")):
    try:
        chat_log = json.loads(json_str)
    except JSONDecodeError:
        logger.error("json字符串错误!")
        await CreateConversationWithJson.finish("Json错误！", at_sender=True)
    if not chat_log[0].get("role"):
        await CreateConversationWithJson.finish("Json错误！", at_sender=True)
    user_id: int = int(event.get_user_id())
    group_id: str = get_group_id(event)
    session: Session = session_container.create_with_chat_log(chat_log, user_id, group_id,
                                                              name=chat_log[0].get('content', '')[:5])
    await CreateConversationWithJson.send(f"创建并加入会话 '{session}' 成功!", at_sender=True)
