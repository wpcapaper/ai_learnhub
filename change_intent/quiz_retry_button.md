# 刷题模式批次完成页新增"开启新的批次"按钮

## 需求描述

在刷题模式的批次完成页面，"返回课程"按钮左侧新增"开启新的批次"按钮。这个按钮的显示前提条件是当前批次所属课程还有未刷过的题。

## 业务逻辑

- 当用户完成一个批次后，系统需要判断该课程是否还有未刷过的题
- 如果还有未刷过的题，则显示"开启新的批次"按钮
- 用户点击"开启新的批次"按钮后，直接开启一个新的批次（无需返回课程页重新选择）
- 如果该课程所有题目都已刷完，则不显示"开启新的批次"按钮

## 技术方案

### 前端实现

1. **修改文件**：`src/frontend/app/quiz/page.tsx`

2. **新增状态**：
   - 添加 `canStartNewBatch` 状态，用于存储是否可以开启新批次
   - 添加 `checkingNewBatch` 状态，用于显示加载状态

3. **新增方法**：
   - `checkCanStartNewBatch()`: 检查是否可以开启新批次（调用 `getNextQuestions` API）
   - `handleStartNewBatch()`: 处理开启新批次的逻辑（调用 `startBatchDirect`）

4. **UI 修改**：
   - 在批次完成页面的"返回课程"按钮左侧添加"开启新的批次"按钮
   - 根据 `canStartNewBatch` 状态决定是否显示该按钮
   - 添加加载状态提示

### API 调用

使用现有的 API 方法：
- `apiClient.getNextQuestions()`: 检查是否还有未刷过的题
- `apiClient.startBatch()`: 开启新批次

### 显示条件

"开启新的批次"按钮的显示条件：
1. 当前批次已完成（`completed === true`）
2. 当前课程还有未刷过的题（`getNextQuestions` 返回题目数 > 0）
3. 已登录（`userId` 不为空）
4. 已选择课程（`courseId` 不为空）

## 工作量评估

- **风险等级**：低
- **涉及范围**：仅前端 UI 和逻辑添加
- **数据库变更**：无
- **后端 API 变更**：无（使用现有 API）
- **预计工时**：2-3 小时

## 实施步骤

1. 在 `QuizContent` 组件中添加新状态（`canStartNewBatch`, `checkingNewBatch`）
2. 添加 `checkCanStartNewBatch` 方法，在批次完成后调用
3. 添加 `handleStartNewBatch` 方法，处理开启新批次的逻辑
4. 修改批次完成页面的 UI，在"返回课程"按钮左侧添加"开启新的批次"按钮
5. 根据 `canStartNewBatch` 状态控制按钮显示
6. 添加中文注释，说明关键业务逻辑
7. 测试验证功能

## 关键代码逻辑

### 检查是否可以开启新批次

```typescript
const checkCanStartNewBatch = async () => {
  if (!userId || !courseId) return;

  setCheckingNewBatch(true);
  try {
    // 尝试获取下一批题目，如果返回题目数 > 0，说明还有未刷过的题
    const nextQuestions = await apiClient.getNextQuestions(userId, course_type || 'exam', 1);
    setCanStartNewBatch(nextQuestions.length > 0);
  } catch (error) {
    console.error('Failed to check new batch availability:', error);
    setCanStartNewBatch(false);
  } finally {
    setCheckingNewBatch(false);
  }
};
```

### 开启新批次

```typescript
const handleStartNewBatch = async () => {
  if (!userId || !courseId) return;

  // 关键业务逻辑：开启新批次，重置答题状态
  await startBatchDirect(userId, courseId);
};
```

## 验收标准

1. 批次完成后，系统自动检查是否还有未刷过的题
2. 如果还有未刷过的题，显示"开启新的批次"按钮
3. 如果所有题目都已刷完，不显示"开启新的批次"按钮
4. 点击"开启新的批次"按钮后，直接开启新批次，无需返回课程页
5. 添加了完整的中文注释，说明关键业务逻辑
6. 功能通过测试验证

## 风险点

无显著风险。使用现有 API，不涉及数据库和后端变更。
