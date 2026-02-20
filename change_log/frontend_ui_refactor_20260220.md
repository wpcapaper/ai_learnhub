# Frontend UI 重构 - 简化与护眼优化

**日期**: 2026-02-20  
**类型**: UI/UX 重构  
**影响范围**: frontend

---

## 一、重构背景

原有 frontend 存在以下问题：
1. **学习统计模块无业务价值**：初期设计，后续演进中逐渐失去作用
2. **首页冗余按钮**：课程首页有多个无意义的快捷入口
3. **代码块样式丑陋**：配色与主题不搭配，字体难看（Geist Mono 手写风格）
4. **视觉不和谐**：卡片无边框，炫技成分过多（BorderBeam、粒子动画等）
5. **主题切换不完整**：切换深色主题后部分文字颜色不可见
6. **AI 助手样式问题**：对话气泡丑陋、默认图标不可见
7. **学习页面滚动问题**：内容可以被滚出屏幕
8. **课程卡片交互不直观**：按钮需要 hover 才显示
9. **课程标题过长**：标签被挤压换行，标题截断后无法查看全名

---

## 二、变更内容

### 2.1 移除学习统计模块

```
删除文件：
- src/frontend/app/stats/page.tsx

修改文件：
- src/frontend/app/page.tsx          # 移除首页统计卡片
- src/frontend/app/courses/page.tsx  # 移除顶部"统计"按钮
- src/frontend/app/mistakes/page.tsx # 移除顶部"统计"按钮
```

### 2.2 预置 JetBrains Mono 字体

```
新增文件：
- src/frontend/public/fonts/JetBrainsMono-Regular.ttf
- src/frontend/public/fonts/JetBrainsMono-Bold.ttf
- src/frontend/public/fonts/JetBrainsMono-Italic.ttf
- src/frontend/public/fonts/JetBrainsMono-BoldItalic.ttf
```

### 2.3 简化主题系统

从四套主题简化为两套：
- **浅色（默认）**：暖白背景 #faf9f7，适合长时间学习
- **深色**：柔和灰色 #141416，适合夜间使用

### 2.4 简化首页

移除花哨效果：
- Particles 粒子动画
- BorderBeam 边框光效
- MagicCard 渐变卡片
- ShimmerButton 闪光按钮

改用简洁卡片：
```tsx
<div style={{
  background: 'var(--card-bg)',
  border: '1px solid var(--card-border)',
  borderRadius: 'var(--radius-lg)',
}}>
```

### 2.5 重建刷题/错题/考试页面

使用 batch API 替代 review API，简化样式移除 Particles/MagicCard：

```
重建文件：
- src/frontend/app/quiz/page.tsx     # 使用 startBatch/submitBatchAnswer/finishBatch
- src/frontend/app/mistakes/page.tsx # 简化样式
- src/frontend/app/exam/page.tsx     # 简化样式
```

### 2.6 课程卡片标签布局修复

**问题**：长课程名导致"学习类/考试类"标签被挤压换行

**解决**：
```tsx
<div className="flex items-center gap-3 mb-3">
  <span className="flex-shrink-0">...</span>  {/* 标签不换行 */}
  <h2 className="truncate" title={course.title}>...</h2>  {/* 标题过长截断，hover 显示全名 */}
</div>
```

### 2.7 课程页面 - 学习类课程隐藏无意义按钮

**问题**：学习类课程如果没有题目，刷题和错题按钮没有意义

**解决**：判断 `total_questions` 动态显示按钮，并调整网格布局

```tsx
<div className={`grid gap-2 ${(course.total_questions || 0) > 0 || course.course_type === 'exam' ? 'grid-cols-3' : 'grid-cols-1'}`}>
```

### 2.8 课程卡片按钮常驻

**问题**：按钮需要 hover 才显示，用户不知道有这些功能

**解决**：移除 `opacity-0 group-hover:opacity-100 transition-opacity`，移除 `group` 类

### 2.9 Markdown 深色主题完整适配

**问题**：切换深色主题后很多文字还是黑色的看不到

**涉及文件**：
- `src/frontend/components/MarkdownReader.tsx`
- `src/frontend/components/LaTeXRenderer.tsx`
- `src/frontend/app/globals.css`

**解决方案**：

1. **LaTeXRenderer**：移除硬编码 `text-gray-900`，改用 `var(--foreground)`

2. **新增 CSS 变量**（浅色/深色两套）：
   ```css
   /* 浅色主题 */
   --code-bg: #1e1e1e;
   --code-header-bg: #252526;
   --code-border: #333;
   --code-text: #d4d4d4;
   --code-inline-bg: #282828;
   --code-lang-default: #888;
   
   /* 深色主题 */
   --code-bg: #0d0d0e;
   --code-header-bg: #161618;
   --code-border: #2a2a2c;
   --code-text: #c9c9c9;
   --code-inline-bg: #1a1a1c;
   --code-lang-default: #6b6b6b;
   ```

3. **所有 Markdown 元素使用 CSS 变量**：h1/h2/h3、p、ul/ol/li、a、blockquote、table/th/td、code

### 2.10 代码块字体阴影移除

**问题**：代码块字体有阴影效果，违背设计共识

**解决**：在 MarkdownReader 和 globals.css 中添加 `textShadow: 'none'` 和 `boxShadow: 'none'`

### 2.11 Markdown 字号增大

**问题**：字号太小容易视觉疲劳

**解决**：
- 文档模式字号从 16px 增加到 17px
- 行高从 1.7 增加到 1.8
- 列表项行高 1.7
- 代码块行高 1.6

### 2.12 Mermaid 图表渲染支持

**新增依赖**：`mermaid` 包

**新增组件**：`MermaidDiagram` 组件，动态渲染 mermaid 代码块为 SVG 图表

```tsx
// MarkdownReader.tsx
if (language === 'mermaid') {
  return (
    <div style={{ margin: '16px 0' }}>
      <MermaidDiagram code={codeContent} />
    </div>
  );
}
```

**注意**：移除了 mermaid 语言标签，既然能画图就不需要显示标签了

### 2.13 AI 助手优化

**问题 1**：对话气泡丑陋（渐变背景、阴影、奇怪圆角）

**问题 2**：默认图标不可见（SVG 路径错误）

**解决方案**：

1. **简化气泡样式**：
   - 移除渐变背景，改用纯色 `var(--primary)` 和 `var(--background-secondary)`
   - 移除阴影 `shadow-lg`
   - 使用统一圆角 `var(--radius-md)`
   - 简化后续问题按钮样式

2. **修复默认图标**：
   ```tsx
   // 使用正确的 SVG 路径
   <svg viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
     <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813..." />
   </svg>
   ```

### 2.14 学习页面滚动修复

**问题**：页面可以整体滚动，导致 Markdown 和 AI 聊天框被滚出屏幕

**解决方案**：

1. **禁止页面整体滚动**：
   ```tsx
   useEffect(() => {
     document.documentElement.style.overflow = 'hidden';
     document.body.style.overflow = 'hidden';
     return () => {
       document.documentElement.style.overflow = '';
       document.body.style.overflow = '';
     };
   }, []);
   ```

2. **使用 flex 布局固定区域**：
   ```tsx
   <div className="h-screen flex flex-col overflow-hidden">
     <nav className="flex-shrink-0">...</nav>
     <div className="flex-1 flex flex-col overflow-hidden">
       <div className="flex-1 flex gap-4 min-h-0">
         {/* Markdown 和 AI 助手区域各自内部滚动 */}
       </div>
     </div>
   </div>
   ```

---

## 三、护眼配色

### 浅色主题（默认）

| 变量 | 值 | 用途 |
|------|-----|------|
| --background | #faf9f7 | 页面背景（暖白） |
| --foreground | #2d3748 | 主文字（深灰） |
| --primary | #5b6be0 | 强调色（靛蓝） |
| --card-bg | #ffffff | 卡片背景 |
| --card-border | #e8e5e1 | 卡片边框 |
| --code-bg | #1e1e1e | 代码块背景 |
| --code-text | #d4d4d4 | 代码块文字 |

### 深色主题

| 变量 | 值 | 用途 |
|------|-----|------|
| --background | #141416 | 页面背景 |
| --foreground | #e8e6e3 | 主文字（暖白） |
| --primary | #7c7ff0 | 强调色（紫） |
| --card-bg | #1e1e21 | 卡片背景 |
| --card-border | rgba(255,255,255,0.08) | 卡片边框 |
| --code-bg | #0d0d0e | 代码块背景 |
| --code-text | #c9c9c9 | 代码块文字 |

---

## 四、验证方法

1. 启动 Docker 服务：
   ```bash
   docker-compose up -d --build frontend
   ```

2. 访问前端：http://localhost:3000

3. 检查项目：
   - 主题切换：浅色/深色所有文字可见
   - 代码块：无阴影、JetBrains Mono 字体、背景适配主题
   - 课程卡片：按钮常驻、标签不换行、长标题 hover 显示全名
   - 学习页面：内容不会滚出屏幕
   - Mermaid 图表：正确渲染为 SVG
   - AI 助手：气泡简洁、图标可见

---

## 五、关键业务逻辑注释位置

- `src/frontend/app/page.tsx`: handleCreateUser（创建用户）、handleSwitchUser（切换用户）
- `src/frontend/app/courses/page.tsx`: handleStartQuiz（刷题模式逻辑）
- `src/frontend/components/MarkdownReader.tsx`: rewriteImageUrl（图片路径重写）、handleScroll（滚动进度跟踪）
- `src/frontend/app/learning/page.tsx`: useEffect（禁止页面滚动）

---

## 六、涉及文件汇总

```
修改文件：
- src/frontend/app/page.tsx
- src/frontend/app/courses/page.tsx
- src/frontend/app/chapters/page.tsx
- src/frontend/app/learning/page.tsx
- src/frontend/app/exam/page.tsx
- src/frontend/app/quiz/page.tsx
- src/frontend/app/mistakes/page.tsx
- src/frontend/app/globals.css
- src/frontend/app/context.tsx
- src/frontend/components/MarkdownReader.tsx
- src/frontend/components/LaTeXRenderer.tsx
- src/frontend/components/AIAssistant.tsx
- src/frontend/components/ThemeSelector.tsx
- src/frontend/package.json（新增 mermaid 依赖）

删除文件：
- src/frontend/app/stats/page.tsx
- src/frontend/app/design-preview/page.tsx

新增文件：
- src/frontend/public/fonts/JetBrainsMono-Regular.ttf
- src/frontend/public/fonts/JetBrainsMono-Bold.ttf
- src/frontend/public/fonts/JetBrainsMono-Italic.ttf
- src/frontend/public/fonts/JetBrainsMono-BoldItalic.ttf
```
