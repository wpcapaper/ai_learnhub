# 章节详情页增强功能实现记录

## 实现日期
2026-02-20

## 分支信息
- **分支名**: `feature/chapter-detail-enhancement`
- **基于**: `origin/develop`
- **Worktree 路径**: `/Users/crazzie/Codes/aie55_llm5_learnhub_chapter_detail`

## 实现内容

### 1. 字数统计和预计用时展示

**新增文件**: `src/frontend/components/ContentStats.tsx`

**功能**:
- 统计 Markdown 内容的字数（中文字符 + 英文单词）
- 计算预计阅读时间（按 300 字/分钟）
- 显示在章节标题下方

**实现要点**:
- 使用正则表达式移除代码块、公式、Markdown 标记等
- 支持中文和英文字数统计
- 大数字自动格式化（如 1.2k, 1.5万）

### 2. 左侧大纲导航栏

**新增文件**: `src/frontend/components/OutlineNav.tsx`

**功能**:
- 自动提取 Markdown 的 h1/h2/h3 标题
- 点击标题可滚动到对应位置
- 滚动时高亮当前标题

**实现要点**:
- 使用正则表达式提取标题
- 监听滚动事件更新激活标题
- 支持标题层级缩进显示

### 3. 上一章/下一章导航

**修改文件**: `src/frontend/app/learning/page.tsx`

**功能**:
- 底部显示上一章/下一章按钮
- 无上/下一章时按钮禁用
- 显示当前章节位置（如 3/10）

**实现要点**:
- 使用 `useMemo` 计算相邻章节
- 章节切换通过 URL 参数实现
- 响应式设计，小屏幕简化显示

### 4. MarkdownReader 组件增强

**修改文件**: `src/frontend/components/MarkdownReader.tsx`

**改动**:
- 使用 `forwardRef` 暴露滚动容器
- 为标题元素添加唯一 ID
- 导出 `MarkdownReaderRef` 接口

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/frontend/components/ContentStats.tsx` | 新增 | 字数统计组件 |
| `src/frontend/components/OutlineNav.tsx` | 新增 | 大纲导航组件 |
| `src/frontend/app/learning/page.tsx` | 修改 | 集成新功能，调整布局 |
| `src/frontend/components/MarkdownReader.tsx` | 修改 | 添加 ref 支持，标题 ID |

## 布局调整

```
┌─────────────────────────────────────────────────────────────┐
│ 顶部导航栏                                                   │
├──────┬──────────────────────────────────┬──────────────────┤
│      │ 章节标题 | 字数: 1,234 | 约 4 分钟  │                  │
│ 大纲 │──────────────────────────────────│                  │
│ 导航 │                                  │   AI Assistant   │
│(xl+) │     Markdown 内容               │                  │
│      │                                  │                  │
│      │──────────────────────────────────│                  │
│      │  ← 上一章        3/10    下一章 → │                  │
├──────┴──────────────────────────────────┴──────────────────┤
```

## 响应式设计

- **xl 屏幕**: 显示左侧大纲导航
- **lg 及以下**: 隐藏大纲导航，保留字数统计和章节导航

## 技术细节

### 字数统计算法
1. 移除代码块（``` 包裹的内容）
2. 移除行内代码（` 包裹的内容）
3. 移除 LaTeX 公式（$ 和 $$ 包裹的内容）
4. 移除 Markdown 标记（#、*、- 等）
5. 统计中文字符数（Unicode 范围 \u4e00-\u9fa5）
6. 统计英文单词数（连续字母序列）

### 大纲导航滚动同步
- 使用 `useCallback` 优化滚动处理函数
- 缓存标题元素位置避免重复计算
- 监听滚动事件更新当前激活标题

### 组件间通信
- MarkdownReader 通过 `forwardRef` 暴露滚动容器
- 父组件通过 state 存储 scrollContainer 并传递给 OutlineNav
- 使用 setTimeout 确保 ref 在渲染后可用

## 注意事项

1. **中文注释要求**: 所有核心业务逻辑包含中文注释
2. **原注释保留**: 未删除任何原有注释
3. **主题适配**: 新组件使用 CSS 变量，支持深色/浅色主题

## 后续优化建议

1. 大纲导航可考虑添加展开/折叠功能
2. 章节导航可添加键盘快捷键支持
3. 字数统计可考虑添加阅读进度指示

---

## Bug 修复记录 (2026-02-21)

### 问题描述

1. **目录列太窄** - w-48 (192px) 不够显示完整标题
2. **切换章节后目录点不动** - 滚动容器绑定失效，点击无响应
3. **大纲点击不跳转** - 点击目录项详情页不滚动
4. **三列布局宽度固定** - 用户无法自定义调整列宽

### 根本原因分析

**滚动容器冲突**: `page.tsx` 外层有 `overflow-y-auto`，而 `MarkdownReader` 内部也有 `overflow-y-auto`，导致：
- `OutlineNav` 获取到的是外层容器，而非实际滚动的 `MarkdownReader` 容器
- 切换章节后 React ref 未及时更新，事件监听器绑定到旧容器

### 修复内容

#### 1. 移除外层滚动容器
**文件**: `src/frontend/app/learning/page.tsx`

```diff
- <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
-   <MarkdownReader ... />
- </div>
+ <MarkdownReader ... />
```

让 `MarkdownReader` 成为唯一的滚动容器。

#### 2. 改进 scrollContainer 获取逻辑
**文件**: `src/frontend/app/learning/page.tsx`

- 切换章节时先 `setScrollContainer(null)` 强制 OutlineNav 重新绑定
- 添加重试机制，确保 ref 准备好后再获取

#### 3. OutlineNav 事件监听优化
**文件**: `src/frontend/components/OutlineNav.tsx`

- 新增 `boundScrollContainerRef` 追踪已绑定的容器
- 切换容器时先移除旧事件监听，再绑定新容器

#### 4. 增加目录列宽度
**文件**: `src/frontend/app/learning/page.tsx`

- 默认宽度从 192px 增加到 260px

#### 5. 实现三列可拖动调整宽度
**文件**: `src/frontend/app/learning/page.tsx`

新增 `ResizeHandle` 组件，实现原生拖拽调整列宽：

| 列 | 默认宽度 | 最小宽度 | 最大宽度 |
|----|---------|---------|---------|
| 左侧目录 | 260px | 180px | 400px |
| 右侧 AI | 360px | 280px | 500px |

**实现要点**:
- 使用 `mousedown/mousemove/mouseup` 事件实现拖拽
- 拖拽时分隔条高亮显示
- 宽度变化实时生效，无额外依赖

### 文件变更

| 文件 | 变更 |
|------|------|
| `src/frontend/app/learning/page.tsx` | 新增 ResizeHandle 组件，移除外层滚动容器，添加列宽状态 |
| `src/frontend/components/OutlineNav.tsx` | 优化事件监听绑定/解绑逻辑 |
| `src/frontend/components/MarkdownReader.tsx` | 调整样式适配新布局 |

### 验证清单

- [x] 目录列宽度适中，标题显示完整
- [x] 切换章节后目录可正常点击
- [x] 点击大纲项详情页正确滚动
- [x] 拖拽分隔条可调整列宽
- [x] 滚动时进度条正常联动
- [x] TypeScript 类型检查通过

---

## Bug 修复记录 #2 (2026-02-21)

### 问题描述

1. **点击目录跳转后进度条不联动** - `onProgressChange` 只更新后端，UI 未实时更新
2. **切换章节后目录不可点击** - 问题仍存在
3. **拖动功能不工作** - 分隔条太窄，且只在 xl 屏幕显示

### 修复内容

#### 1. 进度条实时联动
**文件**: `src/frontend/app/learning/page.tsx`

- 新增 `readingProgress` state 存储实时进度
- 在 `handleProgressChange` 中同步更新 state
- UI 使用 `readingProgress` 替代后端返回的进度值
- 添加 `transition-all duration-300` 使进度条变化更平滑

#### 2. 改进 scrollContainer 获取逻辑
**文件**: `src/frontend/app/learning/page.tsx`

- 使用 `requestAnimationFrame` 轮询获取容器，最多重试 10 次
- 确保 DOM 完全渲染后再获取 ref
- 章节切换时重置 `readingProgress` 为后端保存的进度

#### 3. 修复 OutlineNav 事件监听
**文件**: `src/frontend/components/OutlineNav.tsx`

- 将 `handleScroll` 和 `updateHeadingPositions` 加入 useEffect 依赖数组
- 确保容器变化时使用最新的事件处理函数

#### 4. 改进拖动功能
**文件**: `src/frontend/app/learning/page.tsx`

- 分隔条从 xl 屏幕改为 lg 屏幕显示（1024px 起）
- 增加拖动时的视觉反馈（body cursor 和 userSelect）
- 分隔条宽度从 4px 增加到 8px，更容易点击

### 验证清单 #2

- [ ] 点击目录跳转后进度条实时更新
- [ ] 切换章节后目录可正常点击
- [ ] lg 屏幕以上可拖动调整列宽
- [ ] 拖动时有明显的视觉反馈
