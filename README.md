<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# 多功能ChatGPT插件

✨基于chatGPT API的nonebot插件✨  
<a href="https://pypi.python.org/pypi/nonebot-plugin-chatgpt-on-qq">
<img src="https://img.shields.io/pypi/v/nonebot-plugin-chatgpt-on-qq.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">

</div>

## 介绍

### 会话

- [x] 支持上下文记忆（默认每个会话（Session）记忆10条记录，可在配置项中自定义设置）
- [x] 支持自动保存与加载全部历史记录（默认每个会话（Session）保留100条历史记录，可在配置项中自定义设置）
- [x] 支持会话以json字符串形式导入导出
    - 支持读取json格式的预设(具体可以参考Presets文件夹中的json文件)，并使预设可作为模板被创建
    - `组合技:可以用/chat new <prmopt>创建空白模板ChatGPT以及后续会话来调教机器人，调教完成后使用/chat dump导出聊天记录json，将user改为system，保存在json文件夹就可以创建一个属于你自己的预设了！`
- [x] 插件自带猫娘等预设模板（prompt）构建会话
    - 1.常规GPT模板
    - 2.猫娘模板
- [x] 以群组为单位管理会话，支持私聊
    - 可以设置是否允许私聊触发插件
    - 群组中可以存在多个会话，会话之间相互独立（私聊暂时只支持同时存在一个会话）
    - 群内所有人都可以加入会话，删除则只有群管理员和会话创建者有权限
    - 支持会话复制会话、删除会话、查看会话列表、查看某个人创建的会话、查看当前会话等，具体查看指令列表

### 配置

- [x] 支持同时使用多个 openai_api_key，失效时自动切换
- [x] 支持不同模型，如`gpt-3.5-turbo-0301`，默认为`gpt-3.5-turbo`
  ，具体可参考[官方文档](https://platform.openai.com/docs/guides/chat/instructing-chat-models)
- [x] 可设置使用gpt的理智值(temperature)，介于0~2之间，较高值如`0.8`会使会话更加随机，较低值如`0.2`
  会使会话更加集中和确定，默认为0.5，具体可参考[官方文档](https://platform.openai.com/docs/api-reference/chat/create)
- [x] 可以设置一次回复最大token数量，具体见配置项
- [x] 可以设置正向与反向代理，具体见配置项

### 指令

- [x] 支持自定义 `chat系` 指令前缀，可在配置项 `change_chat_to` 中设置
    - 例如配置 `change_chat_to="Chat"` 则 `/Chat list` 也能触发 `/chat list` 指令，具体见指令列表
- [x] 支持自定义本插件公共指令前缀 `"\"`，可在配置项 `customize_prefix` 中设置
    - 例如配置 `customize_prefix=""` 置空 则 `chat cp` 也能触发 `/chat cp` 指令，具体见指令列表
    - 本插件公共指令前缀对`chat系` 指令及 `talk` 指令均有效果
- [x] 支持自定义与chatGPT会话指令 `"talk"`，防止因为常用前缀为空时误触发，可在配置项 `customize_talk_cmd` 中设置
    - 例如配置 `customize_talk_cmd="gpt"` 置空 则 `/gpt` 也能触发 `/talk` 指令，具体见指令列表

## 安装

推荐使用 `nb plugin install nonebot-plugin-chatgpt-on-qq` 一键安装

如果使用pip安装需要手动将插件在pyproject.toml中加载

## 配置项

所有 **必填** 为`否`的配置项，都可以不写进配置文件，如果这样做了，则这些配置项会取 **默认值**
中的内容，否则会取配置文件中写入的值，所以如果不清楚具体含义的可以直接不在配置文件中写入这些配置。

唯一 **必填** 的配置项只有 `api_key` ,如果你只有一个api_key，可以直接填写字符串，例如 `api_key="sk-xxx..."`
，如果你有多条key，可以填写字符串列表，例如 `api_key=["sk-xxx...", "sk-yyy...", "sk-zzz..."]`

另外，如果在国内的话，代理虽然不是 **必填** 项，但是没有的话是无法连接到 openai
的，所以算是必填项，正向代理使用 `openai_proxy`
，例如 `openai_proxy="127.0.0.1:1080"` （前提是你有代理，这只是个例子）

`history_max` 和 `history_save_path` 是会话的全部历史记录，保存在本地；`chat_memory_max`
是会话与gpt交互时记忆的上下文最大聊天记录长度，实际上只是全部历史记录中的一部分，可以理解为他的记忆；

`preset_path` 是预设模板存放的文件夹，一般不需要改动

`allow_private` 是否允许私聊触发插件

`customize_prefix` 可以修改插件指令的公共前缀 默认是"/"，可以修改成别的，或者直接使用空字符串 `customize_prefix=""`
则去掉这个前缀

`change_chat_to` 可以修改 `chat系` 指令 中的 "chat" 为自定义字符串，因为电脑版qq /chat xxx
会被自动转换成表情，所以支持自定义。比如 `change_chat_to="Chat"` 就可以让 `\Chat list` 触发 `\chat list` 指令

`customize_talk_cmd` 可以修改 `talk` 指令 中 "talk" 为自定义字符，因为 如果将公共前缀置空的话，"talk"
字符串比较常见可能容易引发误触，可以修改成其他的 比如 `customize_talk_cmd="gpt"` 可以让 `\gpt` 触发 `\talk`

`auto_create_preset_info` 可以设置是否提示根据模板自动创建会话的信息，这条提示信息具体在用户不在任何会话时直接使用 `talk`
指令时触发，如果嫌太过频繁可以关闭。但只能关闭掉自动创建提示，主动创建会话仍旧有提醒。

|           配置项           | 必填  | 类型            |        默认值         |                                   说明                                    |
|:-----------------------:|:---:|---------------|:------------------:|:-----------------------------------------------------------------------:|
|         api_key         |  是  | str/List[str] |                    |      填入你的api_key,类似"sk-xxx..."，支持多个key，以字符串列表形式填入，某个key失效后会自动切换下一个      |
|       model_name        |  否  | str           |  "gpt-3.5-turbo"   |                             模型名称，具体可参考官方文档                              |
|       temperature       |  否  | float         |        0.5         | 设置使用gpt的理智值(temperature)，介于0~2之间，较高值如`0.8`会使会话更加随机，较低值如`0.2`会使会话更加集中和确定 |
|      openai_proxy       |  否  | str           |        None        |                          正向HTTP代理 (HTTP PROXY)                          |
|     chat_memory_max     |  否  | int           |         10         |                          设置会话记忆上下文数量，填入大于2的数字                           |
|       history_max       |  否  | int           |        100         |                        设置保存的最大历史聊天记录长度，填入大于2的数字                         |
|    history_save_path    |  否  | str           | "data/ChatHistory" |                               设置会话记录保存路径                                |
|     openai_api_base     |  否  | str           |        None        |                                  反向代理                                   |
|       preset_path       |  否  | str           |   "data/Presets"   |                              填入自定义预设文件夹路径                               |
|      allow_private      |  否  | bool          |        true        |                              插件是否支持私聊，默认开启                              |
|     change_chat_to      |  否  | str           |        None        |           因为电脑端的qq在输入/chat xxx时候经常被转换成表情，所以支持自定义指令前缀替换"chat"            |
|    customize_prefix     |  否  | str           |        "/"         |                   自定义命令前缀，不填默认为"/"，如果不想要前缀可以填入空字符串 ""                   |
|   customize_talk_cmd    |  否  | str           |       "talk"       |              自定义和GPT会话的命令后缀，为了防止在去除前缀情况下talk因为常见而误触发可以自定义               |
| auto_create_preset_info |  否  | bool          |        true        |          是否发送自动根据模板创建会话的信息，如果嫌烦可以关掉，不过只能关掉自动创建的提示，主动创建的会一直有提醒           |
|       max_tokens        |  否  | int           |        1024        |                              一次最大回复token数量                              |

格式如下:

```
api_key=["sk-xxx...", "sk-yyy...", ...]
model_name="gpt-3.5-turbo" #默认为gpt-3.5-turbo，具体可参考官方文档
temperature=0.5 #理智值，介于0~2之间
openai_proxy="x.x.x.x:xxxxx"
chat_memory_max=10 #填入大于2的数字
history_max=100 #填入大于2的数字
history_save_path="E:/Kawaii" # 填入你的历史会话保存文件夹路径，如果修改最好填绝对路径，不过一般不需要修改，可以直接删掉这一行
openai_api_base = "" #cf workers，空字符串或留空都将不使用
preset_path="E:/Kitty" # 填入你的历史会话保存文件夹路径，如果修改最好填绝对路径，不过一般不需要修改，可以直接删掉这一行
allow_private=true # 是否允许私聊触发插件
change_chat_to="Chat" # 具体效果见上方介绍，如果不需要修改也可以直接删掉这一行
customize_prefix="/" # 具体效果见上方介绍，如果不需要修改也可以直接删掉这一行
customize_talk_cmd="talk" 具体效果见上方介绍，如果不需要修改也可以直接删掉这一行
auto_create_preset_info=false 具体效果见上方介绍，如果不需要修改也可以直接删掉这一行
max_tokens=1024 具体效果见上方介绍，如果不需要修改也可以直接删掉这一行
```

## 基础命令

`/chat` 获取命令菜单  
`/chat new`  根据预制模板prompt创建一个新的会话  
`/chat new` (自定义prompt) (不需要括号，直接跟你的prompt就好)利用后面跟随的prompt作为基础prompt来创建一个新的会话  
`/chat list` 获取当前群所有存在的会话的序号及创建时间  
`/chat list <@user>` 获取当前群查看@的用户创建的对话
`/chat join <id>` 加入list中序号为<id>的会话(不需要尖括号，直接跟id就行)  
`/chat del` 删除当前所在会话
`/chat del <id>` 删除list中序号为<id>的会话(不需要尖括号，直接跟id就行)  
`/chat json` 利用历史会话json来回到一个会话,输入该命令后会提示你在下一个消息中输入json  
`/chat dump` 导出当前对话json字符串格式的上下文信息
`/chat cp <id>` 以id会话为模板进行复制新建加入
`/chat who` 查看当前会话信息
`/talk` (会话内容) 在当前会话中进行会话(同样不需要括号，后面直接接你要说的话就行)

|           指令            |       权限        | 需要@ |  范围   |                    说明                     |
|:-----------------------:|:---------------:|:---:|:-----:|:-----------------------------------------:|
|         `/chat`         |       群员        |  否  | 私聊/群聊 |                  获取命令菜单                   |
|       `/chat new`       |       群员        |  否  | 私聊/群聊 |          根据预制模板prompt创建并加入一个新的会话          |
| `/chat new <自定义prompt>` |       群员        |  否  | 私聊/群聊 |    利用<自定义prompt>作为基础prompt来创建并加入一个新的会话    |
|      `/chat list`       |       群员        |  否  | 私聊/群聊 |           获取当前群所有存在的会话的序号及创建时间            |
|  `/chat list <@user>`   |       群员        |  否  | 私聊/群聊 |             获取当前群查看@的用户创建的对话              |
|    `/chat join <id>`    |       群员        |  否  | 私聊/群聊 |     加入list中序号为<id>的会话(不需要尖括号，直接跟id就行)     |
|       `/chat del`       | 主人/群主/管理员/会话创建人 |  否  | 私聊/群聊 |                 删除当前所在会话                  |
|    `/chat del <id>`     | 主人/群主/管理员/会话创建人 |  否  | 私聊/群聊 |     删除list中序号为<id>的会话(不需要尖括号，直接跟id就行)     |
|      `/chat json`       |       群员        |  否  | 私聊/群聊 | 利用历史会话json来回到一个会话,输入该命令后会提示你在下一个消息中输入json |
|      `/chat dump`       |       群员        |  否  | 私聊/群聊 |           导出当前对话json字符串格式的上下文信息           |
|     `/chat cp <id>`     |       群员        |  否  | 私聊/群聊 |             以id会话为模板进行复制新建加入              |
|       `/chat who`       |       群员        |  否  | 私聊/群聊 |                 查看当前会话信息                  |
|     `/talk <会话内容>`      |       群员        |  否  | 私聊/群聊 |  <会话内容> 在当前会话中进行会话(同样不需要括号，后面直接接你要说的话就行)  |

## 使用效果预览(已过时)  

### 利用模板创建新的会话

![image](https://user-images.githubusercontent.com/33772816/223602899-77ce2c3b-5d0f-40c2-8183-65e8447d9bec.png)

### 与bot进行会话

![image](https://user-images.githubusercontent.com/33772816/223603028-4aeda385-6d29-4c67-b7b3-5295e7d6976b.png)

### 查看所有会话列表

![image](https://user-images.githubusercontent.com/33772816/223603171-da174c03-ed0a-465d-9fa5-078ebee0602c.png)

### 加入其他会话

![image](https://user-images.githubusercontent.com/33772816/223603352-d72309c8-4339-4630-9eb9-8bea855787d5.png)

### 删除会话

![image](https://user-images.githubusercontent.com/33772816/223603427-146a70ae-7e47-404e-8f80-04c98380e5ba.png)

### 导出json

![image](https://user-images.githubusercontent.com/33772816/223603499-52a2893f-14a7-4d58-9b6d-e8b3b3760d3f.png)

### 导入json并创建会话

![image](https://user-images.githubusercontent.com/33772816/223603594-126b4b7a-4184-4129-bd72-fce62a90da8e.png)

