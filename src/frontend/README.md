# AILearn Hub - Frontend

基于 Next.js 14 的 AI 学习系统前端应用，提供刷题、考试、复习等学习功能。

## 项目概述

AILearn Hub 前端是一个现代化的单页应用（SPA），提供直观的用户界面，支持：
- **课程选择**：多课程、多题集切换
- **刷题模式**：批次刷题，实时反馈
- **考试模式**：模拟真实考试环境
- **错题本**：错题查看和针对性练习
- **学习统计**：学习进度和成绩分析

## 技术栈

### 核心框架
- **Next.js 16**: React 框架（App Router）
  - 服务端渲染（SSR）
  - 自动代码分割
  - 文件系统路由
  - API Routes

### 语言
- **TypeScript**: 类型安全的 JavaScript 超集
  - 静态类型检查
  - 更好的 IDE 支持
  - 减少运行时错误

### UI 和样式
- **Tailwind CSS 4**: 实用优先的 CSS 框架
  - 快速 UI 开发
  - 响应式设计
  - 自定义主题
- **React 19**: UI 库

### 数学公式渲染
- **KaTeX**: 快速的数学公式渲染库

### 状态管理
- **React Context API**: 全局状态管理
- **LocalStorage**: 本地数据持久化

### HTTP 客户端
- **Fetch API**: 原生浏览器 API
- 自定义 API Client：封装的 API 请求工具

## 目录结构

```
src/frontend/
├── package.json              # 项目依赖和脚本
├── next.config.ts            # Next.js 配置
├── tsconfig.json             # TypeScript 配置
├── tailwind.config.ts       # Tailwind CSS 配置
├── Dockerfile               # Docker 构建文件
├── public/                  # 静态资源
├── app/                     # App Router（页面目录）
│   ├── layout.tsx           # 根布局
│   ├── page.tsx             # 首页
│   ├── context.tsx          # 全局 Context（用户状态）
│   ├── quiz/                # 刷题页面
│   │   └── page.tsx
│   ├── exam/                # 考试页面
│   │   └── page.tsx
│   ├── mistakes/            # 错题本页面
│   │   └── page.tsx
│   ├── stats/               # 统计页面
│   │   └── page.tsx
│   └── courses/             # 课程页面
│       └── page.tsx
├── components/              # 可复用组件
│   ├── LaTeXRenderer.tsx    # LaTeX 公式渲染组件
│   └── [更多组件...]
├── lib/                     # 工具库
│   ├── api.ts               # API 客户端封装
│   └── [其他工具...]
└── styles/                  # 全局样式
    └── globals.css
```

## 快速开始

### 环境要求

- Node.js 18+
- npm、yarn、pnpm 或 bun

### 安装依赖

```bash
cd src/frontend
npm install
```

### 配置环境变量

创建 `.env.local` 文件：

```env
# 后端 API 地址
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 启动开发服务器

```bash
npm run dev
```

应用运行在：http://localhost:3000

### 构建生产版本

```bash
npm run build
npm start
```

## 开发指南

### 添加新页面

在 `app/` 目录下创建新的文件夹和 `page.tsx` 文件：

```typescript
// app/new-page/page.tsx
'use client';

export default function NewPage() {
  return (
    <div>
      <h1>New Page</h1>
    </div>
  );
}
```

访问路径：`/new-page`

### 创建可复用组件

在 `components/` 目录下创建组件：

```typescript
// components/MyComponent.tsx
interface MyComponentProps {
  title: string;
  onClick?: () => void;
}

export function MyComponent({ title, onClick }: MyComponentProps) {
  return (
    <div className="p-4 border rounded">
      <h2>{title}</h2>
      <button onClick={onClick}>Click me</button>
    </div>
  );
}
```

使用组件：

```typescript
import { MyComponent } from '@/components/MyComponent';

// 在页面中使用
<MyComponent title="Hello" onClick={() => console.log('clicked')} />
```

### 使用 API Client

应用封装了 API Client（`lib/api.ts`），提供了类型安全的 API 调用：

```typescript
import { apiClient } from '@/lib/api';

// 获取用户
const user = await apiClient.getUser(userId);

// 获取课程列表
const courses = await apiClient.getCourses();

// 开始刷题
const batch = await apiClient.startBatch(userId, 'practice', 10);
```

### 全局状态管理

使用 React Context API 管理全局状态（`app/context.tsx`）：

```typescript
import { useApp } from '@/app/context';

function MyComponent() {
  const { user, setUser, createUser, logout } = useApp();

  return (
    <div>
      <p>当前用户: {user?.username}</p>
      <button onClick={() => createUser('nickname')}>创建用户</button>
      <button onClick={logout}>退出登录</button>
    </div>
  );
}
```

### 使用 LaTeX 公式

使用 KaTeX 组件渲染数学公式：

```typescript
import { LaTeXRenderer } from '@/components/LaTeXRenderer';

<LaTeXRenderer content="$E = mc^2$" />
```

### 样式开发

使用 Tailwind CSS 类名进行样式开发：

```typescript
<div className="container mx-auto p-4">
  <h1 className="text-2xl font-bold text-gray-900">Title</h1>
  <button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
    Button
  </button>
</div>
```

## 页面说明

### 首页 (`app/page.tsx`)

应用入口页面，提供：
- 用户创建（如果不存在）
- 课程选择
- 功能入口

### 刷题页面 (`app/quiz/page.tsx`)

批次刷题模式：
- 选择课程
- 开始批次刷题（默认10题）
- 提交答案
- 查看成绩和解析

**关键功能：**
- 批次内答题不显示对错
- 批次结束后统一评分
- 支持跳过题目

### 考试页面 (`app/exam/page.tsx`)

模拟真实考试：
- 选择考试模式（固定题集 / 动态抽取）
- 考试过程中不显示答案
- 考试结束后查看成绩

**关键功能：**
- 支持固定题集考试
- 支持动态抽取（按难度）
- 计时功能（可选）

### 错题本页面 (`app/mistakes/page.tsx`)

查看和管理错题：
- 查看历史错题
- 错题统计
- 一键重试错题

### 统计页面 (`app/stats/page.tsx`)

学习数据分析：
- 总答题数
- 正确率
- 已掌握题目数
- 待复习题目数
- 学习进度

### 课程页面 (`app/courses/page.tsx`)

课程管理：
- 浏览所有课程
- 查看课程详情
- 选择课程进行学习

## 组件说明

### LaTeXRenderer (`components/LaTeXRenderer.tsx`)

渲染 LaTeX 数学公式的组件。

**使用方法：**

```typescript
<LaTeXRenderer content="$$ \int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi} $$" />
```

**支持格式：**
- 行内公式：`$E = mc^2$`
- 块级公式：`$$ \int ... $$`

## API Client 说明

### API 方法

API Client (`lib/api.ts`) 提供以下方法：

**用户管理：**
- `createUser(nickname?, userId?)`: 创建用户
- `getUser(userId)`: 获取用户信息
- `getUserStats(userId)`: 获取用户统计
- `listUsers()`: 列出所有用户
- `resetUserData(userId)`: 重置用户数据

**课程管理：**
- `getCourses(activeOnly?, userId?)`: 获取课程列表
- `getCourse(courseId)`: 获取课程详情

**题集管理：**
- `getQuestionSets(courseId, activeOnly?)`: 获取题集列表
- `getQuestionSetQuestions(setCode)`: 获取题集题目

**刷题模式：**
- `startBatch(userId, mode?, batchSize?, courseId?)`: 开始批次
- `submitBatchAnswer(userId, batchId, questionId, answer)`: 提交答案
- `finishBatch(userId, batchId)`: 完成批次
- `getBatchQuestions(userId, batchId)`: 获取批次题目
- `listBatches(userId, limit?)`: 列出批次
- `getBatch(userId, batchId)`: 获取批次详情

**考试模式：**
- `startExam(userId, totalQuestions?, difficultyRange?, courseId?, questionSetCode?)`: 开始考试
- `submitExamAnswer(userId, examId, questionId, answer)`: 提交考试答案
- `finishExam(userId, examId)`: 完成考试
- `getExamQuestions(userId, examId, showAnswers?)`: 获取考试题目

**复习调度：**
- `getNextQuestions(userId, courseType?, batchSize?)`: 获取下一批复习题目
- `submitAnswer(userId, submission)`: 提交答案
- `getReviewStats(userId)`: 获取复习统计
- `getReviewQueue(userId, limit?)`: 获取复习队列

**错题管理：**
- `getMistakes(userId, courseId?)`: 获取错题列表
- `getMistakesStats(userId, courseId?)`: 获取错题统计
- `retryMistakes(userId, courseId?, batchSize?)`: 重试错题

### TypeScript 类型

API Client 导出以下类型：

- `User`: 用户信息
- `Course`: 课程信息
- `QuestionSet`: 题集信息
- `Question`: 题目信息
- `Batch`: 批次信息
- `QuizResult`: 刷题结果
- `UserStats`: 用户统计
- `ReviewStats`: 复习统计
- `AnswerSubmission`: 答题提交
- `ExamConfig`: 考试配置

## 环境变量

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址 | `http://localhost:8000` |

## Docker 部署

### 构建镜像

```bash
cd src/frontend
docker build -t ailearn-frontend .
```

### 运行容器

```bash
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 ailearn-frontend
```

### 使用 Docker Compose

在项目根目录使用：

```bash
docker-compose up frontend
```

## 开发工具

### 代码格式化

```bash
npm run lint
```

### TypeScript 类型检查

```bash
npx tsc --noEmit
```

### Prettier 格式化

```bash
npm install -D prettier
npx prettier --write .
```

## 测试

### 手动测试

启动开发服务器后，访问 http://localhost:3000 进行手动测试。

### 测试流程

1. **用户创建**：
   - 打开首页
   - 点击创建用户（自动创建临时用户）

2. **刷题流程**：
   - 选择课程
   - 进入刷题页面
   - 完成一批题目
   - 查看成绩和解析

3. **考试流程**：
   - 选择课程
   - 进入考试页面
   - 完成考试
   - 查看成绩

4. **错题查看**：
   - 进入错题本
   - 查看错题统计
   - 重试错题

5. **统计数据**：
   - 进入统计页面
   - 查看学习数据

## 常见问题

### 1. 无法连接到后端 API

**问题**：API 请求失败

**解决**：
- 确保后端服务已启动（http://localhost:8000）
- 检查 `.env.local` 中的 `NEXT_PUBLIC_API_URL` 配置
- 检查浏览器控制台的网络请求

### 2. 页面刷新后用户状态丢失

**问题**：刷新页面后需要重新登录

**解决**：
- 应用使用 `localStorage` 保存用户 ID
- 检查 `context.tsx` 中的 `loadUser` 函数
- 确保浏览器没有禁用 `localStorage`

### 3. TypeScript 类型错误

**问题**：编译时出现类型错误

**解决**：
```bash
# 清除构建缓存
rm -rf .next

# 重新构建
npm run build
```

### 4. 样式不生效

**问题**：Tailwind CSS 类名不生效

**解决**：
- 确保安装了 Tailwind CSS 依赖
- 检查 `tailwind.config.ts` 配置
- 重启开发服务器

### 5. 端口被占用

**问题**：`Error: listen EADDRINUSE: address already in use :::3000`

**解决**：
```bash
# 更换端口
npm run dev -- -p 3001

# 或者杀死占用进程
lsof -ti:3000 | xargs kill -9
```

## 性能优化

### 代码分割

Next.js 自动进行代码分割，但可以通过以下方式优化：

```typescript
// 动态导入组件
import dynamic from 'next/dynamic';

const MyComponent = dynamic(() => import('@/components/MyComponent'), {
  loading: () => <p>Loading...</p>
});
```

### 图片优化

使用 Next.js Image 组件：

```typescript
import Image from 'next/image';

<Image
  src="/logo.png"
  alt="Logo"
  width={200}
  height={200}
/>
```

### 字体优化

使用 `next/font` 优化字体加载（已配置 Geist 字体）。

## 相关文档

- [项目根 README](../../README.md)
- [后端 README](../backend/README.md)
- [Next.js 文档](https://nextjs.org/docs)
- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [TypeScript 文档](https://www.typescriptlang.org/docs/)

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目仅供学习和个人使用。
