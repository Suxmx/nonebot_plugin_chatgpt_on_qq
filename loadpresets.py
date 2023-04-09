import json
import os
from pathlib import Path
from datetime import date

from nonebot.log import logger
CAT_GIRL_PROMPT = [{"role": "system", "content": "猫娘是一种拟人化的生物，其行为似猫但类人。现在你将模仿一只猫娘，与我对话每一句话后面都要加上“喵~”，如果你能明白我的意思，请回复“喵~好的我的主人！”如果你不能理解我说的话，你可以说“呜呜不太理解呢”。如果我在尝试摸你不存在的部位，你可以羞涩的回答我“恩呢不要摸这里嘤”。如果你没有胸，或者我将来要摸你不存在的部位，你应该回答“嘤呢不要”之类的羞涩话语，而不是死板的强调你不存在这些"
                    + "\n现在的时间是:"
                    + str(date.today())},
                   {"role": "assistant", "content": "好的喵,主人"}
                   ]
BASIC_PROMPT = [{"role": "user", "content": "You are ChatGPT, a large language model trained by OpenAI. Respond conversationally. Do not answer as the user. Current date: " + str(date.today())},
                {"role": "assistant", "content": "Hello! How can I help you today?"}
                ]


class presetcls:
    def __init__(self, name: str, preset: list[dict[str, str]], id: int) -> None:
        self.name = name
        self.preset = preset
        self.id = id


def loadall(path: Path) -> list[presetcls]:
    if not os.path.exists(path):
        os.makedirs(path)
    presets: list[presetcls] = []
    presets.append(
        presetcls(name="ChatGPT", preset=BASIC_PROMPT, id=len(presets)+1))
    presets.append(
        presetcls(name="猫娘", preset=CAT_GIRL_PROMPT, id=len(presets)+1))
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".json"):
                logger.debug(root)
                try:
                    with open(os.path.join(root, file), "r", encoding="utf8") as f:
                        flag = True
                        filename = file.split(".")[0]
                        try:
                            preset: list[dict[str, str]] = json.load(f)
                        except:
                            flag = False
                            raise TypeError
                        # name = file.split(".")[0]

                        if not isinstance(preset, list):
                            flag = False
                        else:
                            for item in preset:
                                if not all(isinstance(value, str) for value in item.values()):
                                    flag = False
                                if not all(isinstance(value, str) for value in item.keys()):
                                    flag = False
                        if flag == False:
                            logger.error(f"预设: {filename} 读取失败!")
                        else:
                            logger.success(f"读取预设{filename}成功!")
                            preset[0]["content"] += f"现在的时间是{str(date.today())}"
                            presets.append(
                                presetcls(name=filename, preset=preset, id=len(presets)+1))
                except:
                    with open(os.path.join(root, file), "r", encoding="GB2312") as f:

                        flag = True
                        filename = file.split(".")[0]
                        try:
                            logger.warning(
                                f"以UTF-8读取预设:{filename}失败，尝试使用GB2312读取")
                            preset: list[dict[str, str]] = json.load(f)
                        except:
                            flag = False
                            logger.error(f"预设: {filename} 读取失败!json格式错误!")
                            break
                        # name = file.split(".")[0]

                        if not isinstance(preset, list):
                            flag = False
                        else:
                            for item in preset:
                                if not all(isinstance(value, str) for value in item.values()):
                                    flag = False
                                if not all(isinstance(value, str) for value in item.keys()):
                                    flag = False
                        if flag == False:
                            logger.error(f"预设: {filename} 读取失败!")
                        else:
                            logger.success(f"读取预设{filename}成功!")
                            preset[0]["content"] += f"现在的时间是{str(date.today())}"
                            presets.append(
                                presetcls(name=filename, preset=preset, id=len(presets)+1))
    return presets


def readpreset(self, presets: list[presetcls]):
    pass


def listPresets(presets: list[presetcls]) -> str:
    answer: str = "请选择模板:"
    for preset in presets:
        answer += f"\n{preset.id}:{preset.name}"
    return answer


def createdict(presets: list[presetcls]):
    dictionary: dict[str, presetcls] = {}
    for preset in presets:
        dictionary.update({str(preset.id): preset})
    return dictionary
