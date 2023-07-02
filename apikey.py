import random
from typing import List, Union
from collections import UserString, UserList


class APIKey(UserString):
    def __init__(self, key: str):
        super().__init__(key.strip())
        self.status: bool = True
        self.fail_res: str = ''

    @property
    def key(self) -> str:
        return self.data

    def show(self) -> str:
        return f'[{self.data[:8]}....{self.data[-4:]}]'

    def fail(self, fail_res: str):
        self.status = False
        self.fail_res = fail_res

    def show_fail(self) -> str:
        return f'{self.show()} {self.fail_res}'


class APIKeyPool(UserList):

    def __init__(self, api_keys: Union[str, list]):
        if not api_keys or not (isinstance(api_keys, list) or isinstance(api_keys, str)):
            raise Exception('请输入正确的APIKEY')
        if isinstance(api_keys, str):
            api_keys = [api_keys]
        self.valid_num: int = len(api_keys)
        super().__init__([APIKey(k) for k in api_keys])

    @property
    def api_keys(self) -> List[APIKey]:
        return self.data

    def __len__(self):
        return len(self.api_keys)

    @property
    def len(self) -> int:
        return len(self.api_keys)

    def shuffle(self):
        random.shuffle(self.api_keys)

    def fail_keys(self) -> List[APIKey]:
        return [k for k in self.api_keys if not k.status]

    def show_fail_keys(self) -> str:
        msg = f'当前存在apikey共{len(self.api_keys)}个\n'
        fail_num = len(self.fail_keys())
        self.valid_num = len(self.api_keys) - fail_num
        msg += f'已失效key共{fail_num}个：\n'
        for k in self.fail_keys():
            msg += f'{k.show_fail()}\n'
        return msg.strip()
