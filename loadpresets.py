import json
import os
from pathlib import Path
from datetime import date

from nonebot.log import logger


class presetcls:
    def __init__(self, name: str, preset: list[dict[str, str]], id: int) -> None:
        self.name = name
        self.preset = preset
        self.id = id


def loadall(path: Path) -> list[presetcls]:
    presets: list[presetcls] = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".json"):
                logger.debug(root)
                with open(os.path.join(root, file), "r", encoding="utf8") as f:
                    flag = True
                    filename = file.split(".")[0]
                    try:
                        preset: list[dict[str, str]] = json.load(f)
                    except:
                        flag = False
                        logger.error(f"预设: {filename} 读取失败!")
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
                        # preset.append(
                        #     {"role": "system", "content": f"现在的时间是{str(date.today())}"})
                        preset[0]["content"]+=f"现在的时间是{str(date.today())}"
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


def createdict(presets:list[presetcls]):
    dictionary:dict[str,presetcls]={}
    for preset in presets:
        dictionary.update({str(preset.id):preset})
    return dictionary
