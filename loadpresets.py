import json
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Optional

from nonebot.log import logger
from pydantic import BaseModel, ValidationError, validator

# 尝试引用 chardet，非必须，不存在也不会报错
try:
    import chardet
except ModuleNotFoundError:
    logger.warning('需要安装 chardet 模块')

# 在这里统一写进字典后不需要改动其他地方的代码了
# 字典的key会保存为Preset的name以及文件名
# 字典里value里的 {"time": str(date.today())} 感觉没什么实际意义，在 /chat list 指令中会打印出时间
PRESET_PROMPTS: Dict[str, list] = {
    "ChatGPT": [{"role": "user",
                 "content": "You are ChatGPT, a large language model trained by OpenAI. Respond conversationally. Do not answer as the user. Current date: "},
                {"role": "assistant", "content": "Hello! How can I help you today?"},
                {"time": str(date.today())},
                ],
    "猫娘": [{"role": "system",
              "content": "猫娘是一种拟人化的生物，其行为似猫但类人。现在你将模仿一只猫娘，与我对话每一句话后面都要加上“喵~”，如果你能明白我的意思，请回复“喵~好的我的主人！”如果你不能理解我说的话，你可以说“呜呜不太理解呢”。如果我在尝试摸你不存在的部位，你可以羞涩的回答我“恩呢不要摸这里嘤”。如果你没有胸，或者我将来要摸你不存在的部位，你应该回答“嘤呢不要”之类的羞涩话语，而不是死板的强调你不存在这些"
              },
             {"role": "assistant", "content": "好的喵,主人"},
             {"time": f'\n现在的时间是 {str(date.today())}'},
             ],
}


class Preset(BaseModel):
    """
    预设模板类
    """
    name: str
    preset: List[Dict[str, str]]
    preset_id: int
    time: str = None

    @validator('preset')
    def preset_validator(cls, v):
        if all(v):
            return v
        raise ValueError('preset 为空')

    @validator('time')
    def time_validator(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except Exception as e:
            print(e)
            return str(date.today())
        return v

    def __str__(self) -> str:
        return f"{self.preset_id}:{self.name}（{self.time}）"

    @staticmethod
    def presets2str(presets: List["Preset"]) -> str:
        """
        根据输入的预设模板列表生成回复字符串
        """
        answer: str = "请选择模板:"
        for preset in presets:
            answer += f"\n{preset}"
        return answer


def CreateBasicPresetJson(path: Path) -> None:
    """
    根据 PRESET_PROMPTS 创建基本预设模板的 json文件
    """
    for name, prompt in PRESET_PROMPTS.items():
        create_preset2json(prompt, path / f"{name}.json")


def create_preset2json(prompt: list, filepath: Path, encoding: str = 'utf8', ensure_ascii: bool = True,
                       **kwargs) -> None:
    """
    根据输入的 prompt和文件路径创建模板 json文件
    如果文件路径已存在则直接返回
    """
    if filepath.exists():
        return
    dir_path: Path = filepath.parent
    file_name: str = filepath.name
    preset_name: str = filepath.stem
    if not dir_path.is_dir():
        logger.info(f"{filepath}文件夹下{preset_name}基础预设不存在,将自动创建{file_name}")
        dir_path.mkdir(parents=True)
    try:
        with open(filepath, 'w', encoding=encoding) as f:
            json.dump(prompt, f, ensure_ascii=ensure_ascii, **kwargs)
    except Exception:
        logger.error(f"创建{file_name}失败!")
    else:
        logger.success(f"创建{file_name}成功!")


def load_preset(filepath: Path, num: int, encoding: str = 'utf8') -> Optional[Preset]:
    """
    加载路径下的模板 json文件
    """
    with open(filepath, 'r', encoding=encoding) as f:
        preset_data: List[dict] = json.load(f)
    try:
        preset: Preset = Preset(
            name=filepath.stem,
            preset=preset_data,
            preset_id=num,
        )
    except ValidationError:
        logger.error(f'预设: {filepath.stem} 读取失败! encoding {encoding}')
        return
    logger.success(f'预设: {filepath.stem} 读取成功!')
    return preset


def get_encoding(file_path: Path) -> str:
    """
    检测文件编码，需要 chardet 依赖
    """
    with open(file_path, 'rb') as f:
        return chardet.detect(f.read()).get('encoding', 'utf8')


def load_all_preset(path: Path) -> List[Preset]:
    """
    加载指定文件夹下所有模板 json文件，返回 Preset列表
    """
    if not path.exists():
        path.mkdir(parents=True)
    presets: List[Preset] = []
    CreateBasicPresetJson(path)
    for file in path.rglob('*.json'):
        preset: Optional[Preset] = load_preset(file, len(presets) + 1)
        if preset is None:
            try:
                preset: Optional[Preset] = load_preset(file, len(presets) + 1, encoding=get_encoding(file))
            except NameError:
                logger.warning(f'{file} 预设文件编码不是utf8读取失败，需要安装 chardet 模块检测文件编码')
        if preset:
            presets.append(preset)
    if len(presets) > 0:
        logger.success(f"此次共成功加载{len(presets)}个预设")
    else:
        logger.error("未成功加载任何预设!")
    return presets
