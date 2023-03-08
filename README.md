# nonebot_plugin_chatgpt_turbo_on_qq
基于chatGPT-3.5-turboAPI的nonebot插件  
## 安装  
推荐使用nb plugin install nonebot_plugin_chatgpt_on_qq 一键安装
## 使用前须知    
使用前请先在env中添加你的api_key  
格式如下:  
```
api_key="填入你的api_key"
```  
## 基础命令与功能  
/chat 获取命令菜单  
/chat create  根据预制模板prompt创建一个新的对话  
/chat create (自定义prompt) (不需要括号，直接跟你的prompt就好)利用后面跟随的prompt作为基础prompt来创建一个新的对话  
/caht list 获取当前群所有存在的对话的序号及创建时间  
/chat join <id> 加入list中序号为<id>的对话(不需要尖括号，直接跟id就行)  
/chat delete <id> 删除list中序号为<id>的对话(不需要尖括号，直接跟id就行)  
/chat json 利用历史对话json来回到一个对话,输入该命令后会提示你在下一个消息中输入json  
/chat dump 导出当前对话的json文件  
/talk (对话内容) 在当前对话中进行对话(同样不需要括号，后面直接接你要说的话就行)  

