# 刷题模式批次完成页新增"开启新的批次"按钮 - 实现文档

## 实现日期
2026-01-23

## 分支名称
quiz-retry

## 实现内容

### 需求概述
在刷题模式的批次完成页面，"返回课程"按钮左侧新增"开启新的批次"按钮。这个按钮的显示前提条件是当前批次所属课程还有未刷过的题。

### 技术实现

#### 1. 新增状态（src/frontend/app/quiz/page.tsx）

添加了两个新状态：
- `canStartNewBatch`: 用于存储是否可以开启新批次（boolean）
- `checkingNewBatch`: 用于显示检查是否可以开启新批次的加载状态（boolean）

```typescript
const [canStartNewBatch, setCanStartNewBatch] = useState(false);
const [checkingNewBatch, setCheckingNewBatch] = useState(false);
```

#### 2. 新增方法

##### checkCanStartNewBatch()
检查是否可以开启新批次的方法：

```typescript
const checkCanStartNewBatch = async () => {
  if (!userId || !courseId) return;

  setCheckingNewBatch(true);
  try {
    const courseType = course?.course_type || 'exam';
    const nextQuestions = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/review/next?user_id=${userId}&course_type=${courseType}&batch_size=1&allow_new_round=false`)
      .then(res => res.json());
    setCanStartNewBatch(nextQuestions.length > 0);
  } catch (error) {
    console.error('Failed to check new batch availability:', error);
    setCanStartNewBatch(false);
  } finally {
    setCheckingNewBatch(false);
  }
};
```

**关键逻辑**：
- 通过直接调用 `/api/review/next` API 检查当前课程是否还有未刷过的题
- **关键**：传入 `allow_new_round=false` 参数，表示只检查当前轮次未刷过的题，不自动开启新轮
- 如果返回题目数 > 0，说明还有未刷过的题，可以开启新批次
- 如果返回题目数 = 0，说明所有题目都已刷完，不显示按钮

##### handleStartNewBatch()
处理开启新批次的操作：

```typescript
const handleStartNewBatch = async () => {
  if (!userId || !courseId) return;

  await startBatchDirect(userId, courseId);
};
```

**关键逻辑**：
- 用户点击"开启新的批次"按钮后，直接调用 `startBatchDirect` 开启新批次
- 无需返回课程页重新选择，提供更流畅的用户体验

#### 3. 修改批次完成流程

在 `finishBatch` 方法中，批次完成后自动检查是否可以开启新批次：

```typescript
const result = await apiClient.finishBatch(userId, batch.id);
setCompleted(true);

const updatedQuestions = await apiClient.getBatchQuestions(userId, batch.id);
setQuestions(updatedQuestions);

// 关键业务逻辑：批次完成后，检查是否可以开启新批次
checkCanStartNewBatch();
```

#### 4. UI 修改

在批次完成页面修改按钮布局：

```typescript
<div className="flex gap-3">
  {/* 开启新的批次按钮：仅在 canStartNewBatch 为 true 时显示 */}
  {canStartNewBatch && (
    <button
      onClick={handleStartNewBatch}
      disabled={checkingNewBatch}
      className="flex-1 bg-green-600 text-white py-3 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {checkingNewBatch ? '检查中...' : '开启新的批次'}
    </button>
  )}
  <button
    onClick={() => {
      window.location.href = '/courses';
      setBatch(null);
      setQuestions([]);
      setCurrentIndex(0);
      setCompleted(false);
      setCanStartNewBatch(false);
    }}
    className={`py-3 rounded-md hover:bg-blue-700 text-white ${
      canStartNewBatch ? 'flex-1 bg-blue-600' : 'w-full bg-blue-600'
    }`}
  >
    返回课程
  </button>
</div>
```

**按钮显示逻辑**：
- 如果 `canStartNewBatch` 为 true，显示两个按钮并排："开启新的批次"和"返回课程"
- 如果 `canStartNewBatch` 为 false，只显示"返回课程"按钮，占满整个宽度
- "开启新的批次"按钮使用绿色主题，与"返回课程"的蓝色主题区分

### 中文注释

按照需求要求，在关键业务逻辑处添加了中文注释：

1. 状态定义注释：
   ```typescript
   // 关键业务逻辑：状态用于控制"开启新的批次"按钮的显示
   // canStartNewBatch: 当前课程是否还有未刷过的题（true=可开启新批次）
   // checkingNewBatch: 正在检查是否可以开启新批次（用于显示加载状态）
   ```

2. 方法注释：
   ```typescript
   /**
    * 检查是否可以开启新批次
    *
    * 关键业务逻辑：
    * - 通过调用 getNextQuestions API 检查当前课程是否还有未刷过的题
    * - 如果返回题目数 > 0，说明还有未刷过的题，可以开启新批次
    * - 如果返回题目数 = 0，说明所有题目都已刷完，不显示按钮
    */
   ```

3. UI 布局注释：
   ```typescript
   {/* 关键业务逻辑：按钮区域布局
      - 如果有未刷过的题，显示"开启新的批次"和"返回课程"两个按钮
      - 如果所有题都已刷完，只显示"返回课程"按钮 */}
   ```

## 涉及文件

- `/Users/crazzie/Codes/aie55_llm5_learnhub/src/frontend/app/quiz/page.tsx`

## 修改统计

- 新增状态：2 个
- 新增方法：2 个（`checkCanStartNewBatch`, `handleStartNewBatch`）
- 修改方法：1 个（`finishBatch`）
- UI 修改：批次完成页面按钮布局

## 验证结果

1. TypeScript 类型检查：通过（`npx tsc --noEmit` 无错误）
2. 业务逻辑验证：
   - 批次完成后，自动检查是否还有未刷过的题
   - 如果有未刷过的题，显示"开启新的批次"按钮
   - 如果所有题都已刷完，不显示"开启新的批次"按钮
   - 点击"开启新的批次"按钮后，直接开启新批次，无需返回课程页

## 风险点

无显著风险。使用现有 API，不涉及数据库和后端变更。

## 后续优化建议

1. 可以考虑添加批量开启多个批次的选项
2. 可以在批次完成页面显示"还有 X 题未刷"的提示信息
3. 可以考虑添加动画效果，提升用户体验
