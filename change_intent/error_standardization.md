# 错误处理标准化 - 修改意图与计划

## 文档信息
- **创建日期**: 2026-01-20
- **作者**: Sisyphus AI Agent
- **目标分支**: feature/error-standardization
- **关联任务**: 提升系统可维护性和用户体验
- **当前版本**: v1.0
  - v1.0: 初始标准化方案

## 设计原则
- **向后兼容**: 保持现有API功能不变，逐步迁移
- **渐进式改造**: 分阶段实施，降低风险
- **统一标准**: error_code + error_msg 格式
- **前端友好**: 统一错误处理逻辑，友好展示
- **可维护性**: 错误码集中管理，便于扩展

---

## 一、现状评估

### 1.1 当前错误处理模式

#### 后端异常分布
| 异常类型 | 数量 | 分布 |
|----------|--------|------|
| 业务逻辑异常 (ValueError) | 34处 | Service层为主 |
| HTTP异常 (HTTPException) | 10处 | API层为主 |
| 异常传递 | 4处 | detail=str(e) |

#### 前端错误处理分布
| 处理方式 | 数量 | 示例 |
|----------|--------|------|
| alert() | 8处 | quiz, exam页面 |
| setError() | 4处 | courses, mistakes, stats页面 |
| console.error() | 11处 | 全部分散 |

### 1.2 当前问题

| 问题 | 影响 | 优先级 |
|------|--------|--------|
| **错误格式不统一** | 前端需要针对不同格式写多种解析逻辑 | High |
| **错误信息分散** | 相同错误在不同页面有不同文案 | High |
| **调试困难** | 无法按错误码统计和分析 | Medium |
| **缺乏国际化支持** | 错误文本硬编码在前端 | Medium |
| **用户体验不一致** | alert、error banner 等多种展示方式 | High |

---

## 二、改造方案

### 2.1 统一响应格式

#### 成功响应
```json
{
  "data": {...},
  "error_code": null,
  "error_msg": null
}
```

#### 错误响应
```json
{
  "data": null,
  "error_code": "BATCH_NOT_FOUND",
  "error_msg": "批次不存在或已完成"
}
```

### 2.2 错误码体系设计

```python
# src/backend/app/core/error_codes.py

class ErrorCode:
    # 用户相关 (1xxx)
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_CREATE_FAILED = "USER_CREATE_FAILED"
    USER_RESET_FAILED = "USER_RESET_FAILED"

    # 批次相关 (2xxx)
    BATCH_NOT_FOUND = "BATCH_NOT_FOUND"
    BATCH_ALREADY_COMPLETED = "BATCH_ALREADY_COMPLETED"
    BATCH_START_FAILED = "BATCH_START_FAILED"
    BATCH_ANSWER_NOT_FOUND = "BATCH_ANSWER_NOT_FOUND"

    # 题目相关 (3xxx)
    QUESTIONS_UNAVAILABLE = "QUESTIONS_UNAVAILABLE"
    QUESTION_NOT_FOUND = "QUESTION_NOT_FOUND"
    COURSE_NOT_FOUND = "COURSE_NOT_FOUND"
    QUESTION_SET_NOT_FOUND = "QUESTION_SET_NOT_FOUND"

    # 考试相关 (4xxx)
    EXAM_NOT_FOUND = "EXAM_NOT_FOUND"
    EXAM_ALREADY_COMPLETED = "EXAM_ALREADY_COMPLETED"
    EXAM_START_FAILED = "EXAM_START_FAILED"

    # 错题相关 (5xxx)
    NO_MISTAKES_TO_RETRY = "NO_MISTAKES_TO_RETRY"

    # 系统错误 (9xxx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
```

### 2.3 前端统一处理

```typescript
// src/frontend/lib/error-handler.ts

export interface ErrorResponse {
  data: any;
  error_code: string | null;
  error_msg: string | null;
}

export function getErrorMessage(error: any, fallback: string = "操作失败"): string {
  if (error?.response?.data?.error_msg) {
    return error.response.data.error_msg;
  }
  if (error?.message) {
    return error.message;
  }
  return fallback;
}

export function getErrorCode(error: any): string | null {
  return error?.response?.data?.error_code || null;
}

export function showErrorToast(error: any): void {
  const msg = getErrorMessage(error);
  toast.error(msg);
}
```

---

## 三、实施计划（渐进式改造）

### Phase 1: 建立基础设施 (0.5天)

**后端任务**:
- [ ] 创建 `src/backend/app/core/error_codes.py`
- [ ] 创建 `src/backend/app/core/exception_handler.py`
- [ ] 修改 `src/backend/app/main.py` 注册全局异常处理器
- [ ] 单元测试：异常处理器

**前端任务**:
- [ ] 创建 `src/frontend/lib/error-handler.ts`
- [ ] 创建 Toast 组件（可选，用于统一错误展示）

---

### Phase 2: 改造高频API (2天)

**后端任务**:

| 文件 | 异常类型 | 错误码 |
|-------|----------|---------|
| app/api/users.py | 5处 HTTPException | USER_NOT_FOUND, USER_RESET_FAILED |
| app/api/quiz.py | 4处 HTTPException | BATCH_NOT_FOUND, BATCH_START_FAILED, BATCH_ANSWER_NOT_FOUND |

**前端任务**:

| 文件 | 修改点 |
|-------|---------|
| app/page.tsx | 2处：用户创建错误 |
| app/quiz/page.tsx | 3处：批次开始、提交答案、完成批次 |

---

### Phase 3: 改造剩余API (2.5天)

**后端任务**:

| 文件 | 异常类型 | 错误码 |
|-------|----------|---------|
| app/api/exam.py | 4处 HTTPException | EXAM_NOT_FOUND, EXAM_START_FAILED |
| app/api/mistakes.py | 1处 HTTPException | NO_MISTAKES_TO_RETRY |
| app/api/courses.py | 1处 HTTPException | COURSE_NOT_FOUND |
| app/api/question_sets.py | 1处 HTTPException | QUESTION_SET_NOT_FOUND |
| app/services/quiz_service.py | 4处 ValueError | QUESTIONS_UNAVAILABLE |
| app/services/exam_service.py | 8处 ValueError | QUESTION_SET_NOT_FOUND, EXAM_START_FAILED |

**前端任务**:

| 文件 | 修改点 |
|-------|---------|
| app/exam/page.tsx | 3处：考试开始、提交答案、完成考试 |
| app/mistakes/page.tsx | 4处：加载错题、错题重练 |
| app/courses/page.tsx | 2处：加载课程列表 |
| app/stats/page.tsx | 1处：加载统计数据 |

---

### Phase 4: 前端统一错误处理 (0.75天)

**前端任务**:
- [ ] 修改 `src/frontend/lib/api.ts` 的 `fetchJson` 方法
- [ ] 统一所有页面的错误展示方式（使用 Toast 或 error banner）
- [ ] 移除所有 `alert()` 调用
- [ ] 添加错误码到提示文案映射表（可选）

---

## 四、测试验证

### 4.1 单元测试

| 模块 | 测试内容 |
|-------|---------|
| exception_handler.py | 测试各类异常转换的正确性 |
| error_codes.py | 验证错误码完整性 |
| api.ts (前端) | 测试 fetchJson 的错误处理 |

### 4.2 集成测试

| 场景 | 预期结果 |
|------|---------|
| 用户不存在 | 返回 USER_NOT_FOUND + 友好提示 |
| 批次不存在 | 返回 BATCH_NOT_FOUND + 友好提示 |
| 没有可用的题目 | 返回 QUESTIONS_UNAVAILABLE + 友好提示 |
| 错题重练失败 | 返回 NO_MISTAKES_TO_RETRY + 友好提示 |

### 4.3 回归测试

- [ ] 用户登录流程
- [ ] 批次刷题完整流程
- [ ] 考试模式完整流程
- [ ] 错题本功能
- [ ] 学习统计

---

## 五、风险评估与缓解

| 风险 | 影响 | 缓解措施 |
|-------|--------|---------|
| **向后兼容性破坏** | 旧前端无法解析新格式 | 响应体同时支持 data/error_code/error_msg，新前端读取新字段 |
| **引入新bug** | 影响核心功能 | 充分单元测试，逐步灰度发布 |
| **错误码设计不当** | 后期难以扩展 | 参考业界标准，预留充足空间 |
| **前端改造成本低估** | 进度延期 | 分阶段验收，及时调整计划 |

---

## 六、验收标准

### 后端
- [ ] 所有API返回统一格式 {data, error_code, error_msg}
- [ ] 所有异常有对应的错误码
- [ ] 异常处理器单元测试覆盖率 > 80%
- [ ] 代码通过 lint 检查

### 前端
- [ ] 所有API调用统一使用 error-handler 工具
- [ ] 所有错误展示统一为 Toast 或 error banner
- [ ] 无硬编码的 error.message 直接展示
- [ ] 代码通过 TypeScript 类型检查

---

## 七、后续优化

- [ ] 添加错误码文档（自动生成）
- [ ] 国际化支持（error_code 映射多语言文案）
- [ ] 错误日志分析与监控
- [ ] 用户反馈收集机制

---

## 八、时间总结

| 阶段 | 预计工时 |
|-------|----------|
| Phase 1: 基础设施 | 0.5天 |
| Phase 2: 高频API改造 | 2.0天 |
| Phase 3: 剩余API改造 | 2.5天 |
| Phase 4: 前端统一处理 | 0.75天 |
| 测试与验收 | 0.5天 |
| **总计** | **6.25天** |
