import copy
import json
import random
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Set

import openai
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent

from .config import plugin_config
from .loadpresets import templateDict
from .custom_errors import NeedCreatSession, NoResponseError

type_user_id = int
type_group_id = str
PRIVATE_GROUP: str = "Private"

proxy: Optional[str] = plugin_config.openai_proxy
if proxy:
    openai.proxy = {'http': f"http://{proxy}", 'https': f'http://{proxy}'}
else:
    logger.warning("没有设置正向代理")

if plugin_config.openai_api_base:
    openai.api_base = plugin_config.openai_api_base


def get_group_id(event: MessageEvent) -> str:
    if isinstance(event, GroupMessageEvent):  # 当在群聊中时
        return str(event.group_id)
    else:  # 当在私聊中时
        return PRIVATE_GROUP + f'_{event.get_user_id()}'


class SessionContainer:
    def __init__(self, api_keys: List[str], chat_memory_max: int, history_max: int, dir_path: Path,
                 default_only_admin: bool):
        self.api_keys: List[str] = api_keys
        self.chat_memory_max: int = chat_memory_max
        self.history_max: int = history_max
        self.dir_path: Path = dir_path
        self.sessions: List[Session] = []
        self.session_usage: Dict[type_group_id, Dict[type_user_id, Session]] = {}
        self.default_only_admin: bool = default_only_admin
        self.group_auth: Dict[str, bool] = {}
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
        self.load()
        self.load_group_auth()

    @property
    def group_auth_file_path(self) -> Path:
        return self.dir_path / 'group_auth_file.json'

    def save_group_auth(self):
        with open(self.group_auth_file_path, 'w', encoding='utf8') as f:
            json.dump(self.group_auth, f, ensure_ascii=False)

    def load_group_auth(self):
        if not self.group_auth_file_path.exists():
            self.save_group_auth()
            return
        with open(self.group_auth_file_path, 'r', encoding='utf8') as f:
            self.group_auth = json.load(f)

    def get_group_auth(self, gid: str) -> bool:
        return self.group_auth.setdefault(gid, self.default_only_admin)

    def set_group_auth(self, gid: str, auth: bool):
        self.group_auth[gid] = auth
        self.save_group_auth()

    async def delete_session(self, session: "Session", gid: str) -> None:
        group_usage: Dict[int, Session] = self.get_group_usage(gid)
        users = set(uid for uid, s in group_usage.items() if s is session)
        for user in users:
            group_usage.pop(user, None)
        self.sessions.remove(session)
        session.delete_file()
        logger.success(f'成功删除群 {gid} 会话 {session.name}')

    def get_group_sessions(self, group_id: Union[str, int]) -> List["Session"]:
        return [s for s in self.sessions if s.group == str(group_id)]

    @staticmethod
    def old_version_check(session: "Session"):
        if session.group == PRIVATE_GROUP:
            session.file_path.unlink(missing_ok=True)
            session.group = PRIVATE_GROUP + f'_{session.creator}'
            session.save()

    def load(self) -> None:
        for file in list(self.dir_path.glob('*.json')):
            session = Session.reload_from_file(file)
            if not session:
                continue
            self.old_version_check(session)
            self.sessions.append(session)
            group = self.get_group_usage(session.group)
            for user in session.users:
                group[user] = session

    def get_group_usage(self, gid: Union[str, int]) -> Dict[type_user_id, "Session"]:
        return self.session_usage.setdefault(str(gid), {})

    def get_user_usage(self, gid: Union[str, int], uid: int) -> "Session":
        try:
            return self.get_group_usage(gid)[uid]
        except KeyError:
            raise NeedCreatSession(f'群{gid} 用户{uid} 需要创建 Session')

    def create_with_chat_log(self, chat_log: List[Dict[str, str]], creator: int, group: Union[int, str],
                             name: str = '') -> "Session":
        session: Session = Session(chat_log=chat_log, creator=creator, group=group, dir_path=self.dir_path,
                                   name=name, history_max=self.history_max, chat_memory_max=self.chat_memory_max)
        self.get_group_usage(group)[creator] = session
        self.sessions.append(session)
        session.add_user(creator)
        logger.success(f'{creator} 成功创建会话 {session.name}')
        return session

    def create_with_template(self, template_id: str, creator: int, group: Union[int, str]) -> "Session":
        deep_copy: List[Dict[str, str]] = copy.deepcopy(templateDict[template_id].preset)
        return self.create_with_chat_log(deep_copy, creator, group, name=templateDict[template_id].name)

    def create_with_str(self, custom_prompt: str, creator: int, group: Union[int, str], name: str = '') -> "Session":
        custom_prompt = [{"role": "user", "content": custom_prompt}, {
            "role": "assistant", "content": "好"}]
        return self.create_with_chat_log(custom_prompt, creator, group, name=name)

    def create_with_session(self, session: "Session", creator: int, group: str) -> "Session":
        new_session: Session = Session(
            chat_log=session.chat_memory,
            creator=creator,
            group=group,
            name=session.name,
            dir_path=self.dir_path,
            history_max=self.history_max,
            chat_memory_max=self.chat_memory_max,
        )
        self.get_group_usage(group)[creator] = new_session
        self.sessions.append(new_session)
        new_session.add_user(creator)
        logger.success(f'{creator} 成功创建会话 {new_session.name}')
        return new_session


class Session:
    def __init__(self, chat_log: List[Dict[str, str]], creator: int, group: Union[int, str], name: str,
                 chat_memory_max: int, dir_path: Path, history_max: int = 100,
                 users=None, is_save: bool = True, basic_len: int = None):
        self.history: List[Dict[str, str]] = chat_log
        self.creator: int = creator
        self._users: Set[int] = set(users) if users else set()
        self.group: str = group
        self.name: str = name
        self.chat_memory_max: int = chat_memory_max
        self.history_max: int = history_max
        self.creation_time: int = int(datetime.datetime.now().timestamp())
        self.dir_path: Path = dir_path
        if basic_len:
            self.basic_len: int = basic_len
        else:
            self.basic_len = len(self.history)
        if is_save:
            self.save()

    @property
    def prompt(self) -> str:
        return self.history[0].get('content', '').strip()

    def rename(self, name: str) -> None:
        self.file_path.unlink(missing_ok=True)
        self.name = name
        self.save()

    @property
    def users(self) -> Set[int]:
        return self._users

    def add_user(self, user: int) -> None:
        self._users.add(user)
        self.save()

    def del_user(self, user: int) -> None:
        self._users.discard(user)
        self.save()

    def delete_file(self):
        self.file_path.unlink(missing_ok=True)

    @property
    def chat_memory(self) -> List[Dict[str, str]]:
        return self.history[:self.basic_len] + self.history[self.basic_len - self.chat_memory_max:]

    async def ask_with_content(
            self,
            api_keys: List[str],
            content: str,
            role: str = 'user',
            temperature: float = 0.5,
            model: str = 'gpt-3.5-turbo',
            max_tokens=1024,
    ) -> str:
        self.update(content, role)
        return await self.ask(api_keys, temperature, model, max_tokens)

    async def ask(
            self,
            api_keys: List[str],
            temperature: float = 0.5,
            model: str = 'gpt-3.5-turbo',
            max_tokens=1024,
    ) -> str:
        if not api_keys:
            logger.error(
                f'当前不存在api key，请在配置文件里进行配置...')
            return ''
        if _key_load_balancing:
            random.shuffle(api_keys)
        for num, key in enumerate(api_keys):
            openai.api_key = key
            logger.debug(f'当前使用 Api Key [{key[:4]}...{key[-4:]}]')
            try:
                completion: dict = await openai.ChatCompletion.acreate(
                    model=model,
                    messages=self.chat_memory,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=_timeout,
                )
                self.update_from_completion(completion)
                if completion.get("choices") is None:
                    raise NoResponseError("未返回任何choices")
                if len(completion["choices"]) == 0:
                    raise NoResponseError("返回的choices长度为0")
                if completion["choices"][0].get("message") is None:
                    raise NoResponseError("未返回任何文本!")
                logger.debug(f'使用当前 Api Key: [{key[:4]}...{key[-4:]}] 请求成功')
                return completion["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(
                    f'当前 Api Key([{num + 1}/{len(api_keys)}]): [{key[:4]}...{key[-4:]}] 请求错误，尝试使用下一个...')
                logger.warning(
                    f'{type(e)}:{e}'
                )
        return ''

    def update(self, content: str, role: str = 'user') -> None:
        self.history.append({'role': role, 'content': content})
        while len(self.history) > self.history_max:
            self.history.pop(0)
        self.save()

    def update_from_completion(self, completion: dict) -> None:
        role = completion["choices"][0]["message"]["role"]
        content = completion["choices"][0]["message"]["content"]
        self.update(content, role)

    @classmethod
    def reload(cls, chat_log: List[Dict[str, str]], creator: int, group: str, name: str, creation_time: int,
               chat_memory_max: int, dir_path: Path, history_max: int, users: List[int] = None,
               basic_len: int = None) -> "Session":
        session: "Session" = cls(chat_log, creator, group, name, chat_memory_max, dir_path, history_max, users, False,
                                 basic_len)
        session.creation_time = creation_time
        return session

    @classmethod
    def reload_from_file(cls, file_path: Path) -> Optional["Session"]:
        try:
            with open(file_path, 'r', encoding='utf8') as f:
                session: Session = cls.reload(dir_path=file_path.parent, **json.load(f))
                logger.success(f'从文件 {file_path} 加载 Session 成功')
                return session
        except Exception as e:
            logger.error(f'从文件 {file_path} 加载 Session 失败\n{type(e)}:{e}')

    def as_dict(self) -> dict:
        return {
            'chat_log': self.history,
            'creator': self.creator,
            'users': list(self._users),
            'group': self.group,
            'name': self.name,
            'creation_time': self.creation_time,
            'chat_memory_max': self.chat_memory_max,
            'history_max': self.history_max,
            'basic_len': self.basic_len,
        }

    @property
    def file_path(self) -> Path:
        return self.dir_path / f'{self.group}_{self.name}_{self.creator}_{self.creation_time}.json'

    def save(self):
        with open(self.file_path, 'w', encoding='utf8') as f:
            json.dump(self.as_dict(), f, ensure_ascii=False)

    def dump2json_str(self) -> str:
        return json.dumps(self.chat_memory, ensure_ascii=False)


_chat_memory_max = plugin_config.chat_memory_max if plugin_config.chat_memory_max > 2 else 2
_history_max = plugin_config.history_max if plugin_config.history_max > _chat_memory_max else 100
_timeout = int(plugin_config.timeout) if plugin_config.timeout and plugin_config.timeout > 0 else 10
_key_load_balancing: bool = plugin_config.key_load_balancing

session_container: SessionContainer = SessionContainer(
    dir_path=plugin_config.history_save_path,
    chat_memory_max=_chat_memory_max,
    api_keys=plugin_config.api_key,
    history_max=_history_max,
    default_only_admin=plugin_config.default_only_admin,
)
