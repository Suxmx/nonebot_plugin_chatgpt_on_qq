# 多功能ChatGPT插件
基于chatGPT-3.5-turboAPI的nonebot插件  
## 安装  
推荐使用nb plugin install nonebot_plugin_chatgpt_on_qq 一键安装
## 使用前须知    
使用前请先在env中添加你的api_key  
格式如下:  
```
api_key="填入你的api_key"
```  
## 功能  
支持群聊与私聊  
群聊中可同时创建多个会话,对话间相互独立  
对话时会保存一部分上下文信息(2000个token左右,超过会自动从最早的历史记录开始逐步清除)  
能导出导入历史记录一键回到曾经的会话  
有普通chatGPT(id:1)模板基础的猫娘模板(id:2),以及隐藏的诺拉模板(id:3)作为基础prompt来构建对话  
可自动在本地保存所有对话的聊天记录  


## 基础命令  
/chat 获取命令菜单  
/chat create  根据预制模板prompt创建一个新的对话  
/chat create (自定义prompt) (不需要括号，直接跟你的prompt就好)利用后面跟随的prompt作为基础prompt来创建一个新的对话  
/caht list 获取当前群所有存在的对话的序号及创建时间  
/chat join <id> 加入list中序号为<id>的对话(不需要尖括号，直接跟id就行)  
/chat delete <id> 删除list中序号为<id>的对话(不需要尖括号，直接跟id就行)  
/chat json 利用历史对话json来回到一个对话,输入该命令后会提示你在下一个消息中输入json  
/chat dump 导出当前对话的json文件  
/talk (对话内容) 在当前对话中进行对话(同样不需要括号，后面直接接你要说的话就行)  
## 使用效果预览  
### 利用模板创建新的对话  
  ![image](https://user-images.githubusercontent.com/33772816/223602899-77ce2c3b-5d0f-40c2-8183-65e8447d9bec.png)
### 与bot进行对话  
  ![image](https://user-images.githubusercontent.com/33772816/223603028-4aeda385-6d29-4c67-b7b3-5295e7d6976b.png)
### 查看所有对话列表  
  ![image](https://user-images.githubusercontent.com/33772816/223603171-da174c03-ed0a-465d-9fa5-078ebee0602c.png)
### 加入其他对话  
  ![image](https://user-images.githubusercontent.com/33772816/223603352-d72309c8-4339-4630-9eb9-8bea855787d5.png)
### 删除对话  
  ![image](https://user-images.githubusercontent.com/33772816/223603427-146a70ae-7e47-404e-8f80-04c98380e5ba.png)
### 导出json  
  ![image](https://user-images.githubusercontent.com/33772816/223603499-52a2893f-14a7-4d58-9b6d-e8b3b3760d3f.png)
### 导入json并创建对话  
  ![image](https://user-images.githubusercontent.com/33772816/223603594-126b4b7a-4184-4129-bd72-fce62a90da8e.png)

