01-27 ~ 02-04 工作安排

python环境要求 python=3.11
各个小组使用uv或者conda统一依赖，必须有pyproject.toml(uv) 或者 requirements.txt(conda) 约束pip依赖版本
助学Agent模块
Agent编排
●baseline:
○至少完成课程页面答疑助手Agent编排，能基于课程内容回答用户的疑问，能引用课程原文的情况必须引用课程原文
○不允许用户问和课程完全无关的问题
○整理出Agent所需的上下文字段
○至少使用2-3款大模型，并评估在同样prompt情况下的表现
○合理的会话历史管理策略
●extra:
○扩展更多助学Agent的场景
○整理无AI情况下学习的痛点
○思考整理不用我们的系统，单纯使用AI聊天工具学习教程的流程和痛点
○其他关于产品设计上的想法扩展
RAG
●baseline:
○制定合理的文档切割策略，保证一定的召回率
■注意甄别哪些东西能做embedding，哪些不能做
○为助学agent提供检索tool
○实现一个召回测试工具
○评估不同embedding模型的效果
●extra:
○制定更多提升召回率的方法
○虽说是中文场景使用，思考一下教程万一是英文的或者其他语言的应该怎么处理
可视化Agent编排
●baseline:
○实现对教程知识的词云可视化
○实现对教程知识图谱可视化
○至少通过2-3种大模型完成工作，评估其效果
●extra:
○提供助于助学Agent召回的tool
○和RAG联动利用知识图谱等为段落提供元数据


## Fork basics
已设置 upstream。按以下步骤操作：
步骤 1：Fork 仓库
在 Gitee 打开 https://gitee.com/naplus/aie55_llm5_learnhub
点击右上角的 "Fork" 按钮，fork 到你的账户
步骤 2：添加你的 fork 作为 origin
Fork 完成后，告诉我你的 Gitee 用户名，或直接提供 fork 仓库地址，我会帮你添加。
或者你可以手动运行：
git remote add origin git@gitee.com:你的用户名/aie55_llm5_learnhub.git
步骤 3：推送到你的 fork
git push -u origin feat/rag_pilot
步骤 4：创建 Pull Request
在 Gitee 上打开你的 fork 仓库
点击 "Pull Requests" → "新建 Pull Request"
选择从你的 feat/rag_pilot 分支到 naplus/aie55_llm5_learnhub 的相应分支