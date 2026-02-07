# AI 课程助手开发指南

本文档说明如何基于现有的 AI 课程助手接口开发完整的 Agent 功能。

---

## 目录

- [1. 导入 Learning 类型课程](#1-导入-learning-类型课程)
- [2. AI 助手接口说明](#2-ai-助手接口说明)
- [3. 接入真实 AI 模型](#3-接入真实-ai-模型)
- [4. 功能增强建议](#4-功能增强建议)
- [5. 开发注意事项](#5-开发注意事项)

---

## 1. 导入 Learning 类型课程

在开发 AI 助手之前，需要先将课程数据导入数据库。

### 1.1 课程目录结构

```
/courses
├── course-1/
│   ├── course.json          # 课程元数据
│   ├── chapter1.md          # 章节内容（Markdown 格式）
│   ├── chapter2.md
│   └── ...
├── course-2/
│   └── ...
```

### 1.2 course.json 格式

```json
{
  "code": "course-code-001",
  "title": "课程标题",
  "description": "课程描述",
  "cover_image": "https://example.com/cover.jpg",
  "default_exam_config": {
    "total_questions": 50,
    "passing_score": 60
  },
  "sort_order": 1,
  "chapters": [
    {
      "file": "chapter1.md",
      "title": "第一章标题",
      "sort_order": 1
    },
    {
      "file": "chapter2.md",
      "title": "第二章标题",
      "sort_order": 2
    }
  ]
}
```

### 1.3 导入脚本

运行以下命令导入课程：

```bash
# 从项目根目录执行
python scripts/import_learning_courses.py

# 或者指定自定义课程目录
python scripts/import_learning_courses.py /path/to/courses
```

**关键点**：
- 脚本会自动扫描 `/courses` 目录下的所有课程
- 每个课程必须包含 `course.json` 文件
- 章节内容以 Markdown 格式存储
- `course_type` 字段自动设置为 `"learning"`

### 1.4 验证导入成功

导入后可以通过 API 验证：

```bash
curl http://localhost:8000/courses
```

返回包含 `course_type: "learning"` 的课程列表。

---

## 2. AI 助手接口说明

### 2.1 接口地址

```
POST /learning/ai/chat
```

### 2.2 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| chapter_id | string | 是 | 当前学习的章节 ID |
| message | string | 是 | 用户的消息/问题 |
| user_id | string | 否 | 用户 ID（用于个性化或记录对话历史） |

### 2.3 请求示例

```bash
curl -X POST "http://localhost:8000/learning/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "chapter_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "请解释一下这一章的核心概念",
    "user_id": "user-123"
  }'
```

### 2.4 当前响应格式

当前实现返回固定格式的文本响应（流式输出）：

```
当前正在学习的章节ID为:550e8400-e29b-41d4-a716-446655440000
 当前章节markdown为:这是章节内容的前50个字符预览...
阿巴阿巴
```

### 2.5 核心代码位置

文件路径：`src/backend/app/api/learning.py`

关键函数：`ai_chat()`

该函数已包含详细的中文注释，说明：
- 参数验证逻辑
- 数据库查询方式（获取章节内容）
- 响应格式说明
- 后续开发建议

---

## 3. 接入真实 AI 模型

### 3.1 修改 `ai_chat()` 函数

当前的 `generate_stream()` 函数返回固定文本。需要修改为调用真实 AI 模型。

#### 示例：接入 OpenAI GPT

```python
import openai

async def generate_stream():
    """
    生成流式响应（使用 OpenAI GPT）
    """
    # 获取完整章节内容（不截断）
    chapter_content = chapter.content_markdown

    # 构建系统提示词
    system_prompt = f"""
    你是一个专业的课程助手，帮助学生理解课程内容。
    以下是当前章节的内容：

    {chapter_content}

    请基于以上内容回答学生的问题。
    """

    # 调用 OpenAI API
    async for chunk in await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ],
        stream=True
    ):
        if chunk.choices[0].delta.get("content"):
            yield chunk.choices[0].delta.content
```

#### 示例：接入 DeepSeek

```python
import httpx

async def generate_stream():
    """
    生成流式响应（使用 DeepSeek）
    """
    chapter_content = chapter.content_markdown

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": "Bearer YOUR_API_KEY",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": f"请基于以下课程内容回答问题：\n\n{chapter_content}"
                    },
                    {
                        "role": "user",
                        "content": request.message
                    }
                ],
                "stream": True
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield json.loads(line[6:])["choices"][0]["delta"]["content"]
```

### 3.2 环境变量配置

在 `src/backend/.env` 中配置 API 密钥：

```env
# OpenAI
OPENAI_API_KEY=sk-...

# DeepSeek
DEEPSEEK_API_KEY=sk-...

# 其他 AI 服务
...
```

### 3.3 安装依赖

```bash
cd src/backend
pip install openai httpx
```

---

## 4. 功能增强建议

### 4.1 对话历史管理

**目标**：实现多轮对话，AI 能记住之前的对话内容

**实现方式**：
1. 创建 `Conversation` 和 `Message` 模型
2. 在 `ai_chat()` 中查询历史对话
3. 将历史消息传递给 AI 模型

```python
# 新增模型
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    chapter_id = Column(String(36), ForeignKey('chapters.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey('conversations.id'))
    role = Column(String(10))  # 'user' or 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 4.2 RAG（检索增强生成）

**目标**：基于课程内容的语义检索，提高回答准确性

**实现方式**：
1. 使用向量数据库（如 Pinecone、Chroma、Milvus）
2. 对章节内容进行向量化
3. 根据用户问题检索相关内容
4. 将检索结果作为上下文传递给 AI

```python
from sentence_transformers import SentenceTransformer
import chromadb

# 初始化
embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("course_content")

# 检索相关内容
query_embedding = embedder.encode(request.message)
results = collection.query(
    query_embeddings=[query_embedding.tolist()],
    n_results=3
)
```

### 4.3 知识库增强

**目标**：构建基于课程知识库的问答系统

**实现方式**：
1. 使用 LlamaIndex、LangChain 等框架
2. 构建课程文档索引
3. 支持跨章节查询

```python
from llama_index import VectorStoreIndex, SimpleDirectoryReader

# 加载课程文档
documents = SimpleDirectoryReader('/courses').load_data()

# 构建索引
index = VectorStoreIndex.from_documents(documents)

# 查询
query_engine = index.as_query_engine()
response = query_engine.query(request.message)
```

### 4.4 个性化推荐

**目标**：根据用户的学习进度推荐相关内容

**实现方式**：
1. 分析用户的阅读进度（ReadingProgress）
2. 识别薄弱章节
3. 主动推送相关内容

---

## 5. 开发注意事项

### 5.1 数据库操作

- 使用 SQLAlchemy ORM 进行数据库操作
- 通过 `Depends(get_db)` 获取数据库会话
- 查询章节时注意过滤已删除记录：`Chapter.is_deleted == False`

### 5.2 流式响应

- 当前使用 `StreamingResponse` 返回流式响应
- 保持流式格式可以提高用户体验（打字机效果）
- 不同 AI 模型的流式 API 格式不同，需要适配

### 5.3 错误处理

- 验证请求参数（章节 ID、消息内容不能为空）
- 处理章节不存在的情况（返回 404）
- 捕获 AI API 调用失败的情况

### 5.4 性能优化

- 缓存章节内容（避免重复查询数据库）
- 使用异步操作（提高并发性能）
- 考虑对长章节内容进行分段处理

### 5.5 安全性

- 验证用户权限（确保用户只能访问自己的学习记录）
- 避免提示词注入（对用户输入进行过滤）
- 保护 API 密钥（使用环境变量）

---

## 6. 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/backend/app/api/learning.py` | 学习课程 API（包含 AI 助手接口） |
| `src/backend/app/services/learning_service.py` | 学习课程服务层 |
| `src/backend/app/models/chapter.py` | 章节模型 |
| `scripts/import_learning_courses.py` | 课程导入脚本 |

---

## 7. 快速开始

1. **导入课程数据**：
   ```bash
   python scripts/import_learning_courses.py
   ```

2. **测试当前接口**：
   ```bash
   curl -X POST "http://localhost:8000/learning/ai/chat" \
     -H "Content-Type: application/json" \
     -d '{"chapter_id": "your-chapter-id", "message": "测试"}'
   ```

3. **接入 AI 模型**：
   - 修改 `src/backend/app/api/learning.py` 中的 `generate_stream()` 函数
   - 配置 API 密钥
   - 安装依赖包
   - 测试接口

---

## 8. 常见问题

### Q1: 为什么当前返回"阿巴阿巴"？

A: 这是预埋的占位符实现，用于验证接口流程。实际开发时需要替换为真实的 AI 模型调用。

### Q2: 如何获取章节 ID？

A: 通过章节列表接口获取：
```bash
curl http://localhost:8000/learning/{course_id}/chapters
```

### Q3: 支持哪些 AI 模型？

A: 理论上支持任何提供流式 API 的 AI 模型，如 OpenAI GPT、DeepSeek、Claude 等。

### Q4: 如何处理超长章节内容？

A: 可以考虑：
- 对章节进行语义分段
- 只传递相关段落给 AI 模型
- 使用 RAG 技术检索相关内容

---

如有问题，请参考代码中的注释或联系开发团队。
