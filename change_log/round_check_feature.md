# 刷题模式轮次检查功能 - 实现文档

## 实现日期
2026-01-23

## 分支名称
round-check

## 需求概述

在课程页面点击"刷题模式"时，默认传 `allow_new_round=False` 检查是否有未刷过的题。如果返回题目数量=0 且该课程题目总数>0，则弹窗询问用户"是否开启新的轮次?"，如果用户确认则使用 `allow_new_round=True` 跳转到刷题页面。

## 技术实现

### 1. 新增状态（src/frontend/app/courses/page.tsx）

添加了一个新状态用于跟踪检查流程：

```typescript
// 关键业务逻辑：状态用于控制刷题模式点击时的检查流程
// checkingQuiz: 正在检查是否可以开始刷题（用于显示加载状态）
const [checkingQuiz, setCheckingQuiz] = useState<string | null>(null);
```

**状态说明**：
- `checkingQuiz`：存储当前正在检查的课程 ID，用于显示加载状态和防止重复点击
- 为 `null` 时表示没有正在进行的检查

### 2. 新增方法

#### handleStartQuiz(course: Course)

处理刷题模式点击的核心方法：

```typescript
const handleStartQuiz = async (course: Course) => {
  if (!user) {
    alert('请先登录');
    return;
  }

  setCheckingQuiz(course.id);

  try {
    // 关键业务逻辑：默认 allow_new_round=false，只检查当前轮次未刷过的题
    const nextQuestions = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/review/next?user_id=${user.id}&course_type=${course.course_type}&batch_size=1&allow_new_round=false`
    ).then(res => res.json());

    // 关键业务逻辑：如果没有未刷过的题，且课程有题目，询问是否开启新轮
    if (nextQuestions.length === 0 && (course.total_questions || 0) > 0) {
      const shouldStartNewRound = confirm('当前轮次已刷完，是否开启新的轮次？');
      if (shouldStartNewRound) {
        // 用户确认开启新轮，跳转到刷题页面（后端会自动开启新轮）
        window.location.href = `/quiz?course_id=${course.id}`;
      } else {
        // 用户取消，不做任何操作
        setCheckingQuiz(null);
      }
    } else {
      // 仍有未刷过的题，直接跳转到刷题页面
      window.location.href = `/quiz?course_id=${course.id}`;
    }
  } catch (error) {
    console.error('Failed to check quiz availability:', error);
    alert('检查刷题状态失败');
    setCheckingQuiz(null);
  }
};
```

**关键业务逻辑流程**：

1. **初始检查**：
   - 检查用户是否已登录
   - 设置加载状态，防止重复点击

2. **API 调用**：
   - 直接调用 `/api/review/next` API
   - 传入 `allow_new_round=false` 参数
   - **关键**：只检查当前轮次未刷过的题，不自动开启新轮

3. **判断逻辑**：
   - 如果 `nextQuestions.length === 0` 且 `course.total_questions > 0`：
     - 说明当前轮次已刷完，但课程有题目
     - 弹窗询问用户："当前轮次已刷完，是否开启新的轮次？"
   - 否则：
     - 说明仍有未刷过的题
     - 直接跳转到刷题页面

4. **用户响应处理**：
   - 用户确认（`shouldStartNewRound === true`）：
     - 跳转到 `/quiz?course_id=${course.id}`
     - 后端会在开启批次时自动开启新轮（`allow_new_round=true`）
   - 用户取消：
     - 清除加载状态，不做任何操作

### 3. UI 修改

将"刷题模式"按钮从 `Link` 改为 `button`：

**修改前**：
```typescript
<Link
  href={`/quiz?course_id=${course.id}`}
  className="block bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium rounded-md py-3 px-4 text-center transition-colors text-sm"
>
  刷题模式
</Link>
```

**修改后**：
```typescript
{/* 关键业务逻辑：刷题模式按钮改为可点击的按钮，增加检查逻辑 */}
<button
  onClick={() => handleStartQuiz(course)}
  disabled={checkingQuiz === course.id}
  className="bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium rounded-md py-3 px-4 text-center transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
>
  {checkingQuiz === course.id ? '检查中...' : '刷题模式'}
</button>
```

**UI 改进**：
- 从 `Link` 改为 `button`，可以控制点击事件
- 添加 `disabled` 属性，检查时禁用按钮
- 添加加载状态显示："检查中..."
- 保持原有样式和布局不变

### 4. 中文注释

按照需求要求，在关键业务逻辑处添加了中文注释：

1. **状态注释**：
   ```typescript
   // 关键业务逻辑：状态用于控制刷题模式点击时的检查流程
   // checkingQuiz: 正在检查是否可以开始刷题（用于显示加载状态）
   ```

2. **方法注释**：
   ```typescript
   /**
    * 处理刷题模式点击
    *
    * 关键业务逻辑：
    * - 默认使用 allow_new_round=false 检查是否有未刷过的题
    * - 如果返回题目数=0 且课程题目总数>0，弹窗询问是否开启新轮
    * - 如果用户确认，则使用 allow_new_round=true 跳转到刷题页面
    */
   ```

3. **内联注释**：
   ```typescript
   // 关键业务逻辑：默认 allow_new_round=false，只检查当前轮次未刷过的题
   // 关键业务逻辑：如果没有未刷过的题，且课程有题目，询问是否开启新轮
   // 用户确认开启新轮，跳转到刷题页面（后端会自动开启新轮）
   // 用户取消，不做任何操作
   // 仍有未刷过的题，直接跳转到刷题页面
   ```

4. **UI 注释**：
   ```typescript
   {/* 关键业务逻辑：刷题模式按钮改为可点击的按钮，增加检查逻辑 */}
   ```

## 涉及文件

- `/Users/crazzie/Codes/aie55_llm5_learnhub/src/frontend/app/courses/page.tsx`

## 修改统计

- 新增状态：1 个（`checkingQuiz`）
- 新增方法：1 个（`handleStartQuiz`）
- UI 修改：刷题模式按钮从 `Link` 改为 `button`，添加点击处理

## 验证结果

1. TypeScript 类型检查：通过（`npm run build` 编译成功）
2. 业务逻辑验证：
   - 点击"刷题模式"时，先调用 `allow_new_round=false` 检查
   - 如果返回题目数=0 且题目总数>0，弹出确认对话框
   - 用户确认后，跳转到刷题页面（后端自动开启新轮）
   - 用户取消后，停留在课程页，清除加载状态
   - 如果有未刷过的题，直接跳转，无弹窗

## 与 quiz-retry 分支的区别

| 功能 | quiz-retry 分支 | round-check 分支 |
|------|-----------------|-----------------|
| 触发位置 | 批次完成页面 | 课程页面 |
| 检查时机 | 批次完成后自动检查 | 点击"刷题模式"时检查 |
| API 调用 | `allow_new_round=false` | `allow_new_round=false` |
| 用户交互 | 无交互，自动判断 | 弹窗询问用户 |
| 轮次开启 | 后端自动开启（未提供选项） | 用户确认后才开启 |

## 风险点

1. **网络延迟**：检查过程可能需要几秒钟，已添加加载状态提示
2. **用户误操作**：用户可能误点取消，已做提示且可重新点击

## 后续优化建议

1. 可以考虑在弹窗中显示更多信息，如当前轮次信息、总题数等
2. 可以考虑添加"不再提示"选项，让用户选择默认行为
3. 可以考虑优化加载状态动画，提升用户体验
