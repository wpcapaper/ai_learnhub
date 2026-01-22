# 固定题库导入与考试入口功能 - 修改意图与计划

## 文档信息
- **创建日期**: 2026-01-21
- **作者**: Sisyphus AI Agent
- **目标分支**: feature/fixed-question-set
- **关联任务**: 固定题库导入与考试入口功能
- **当前版本**: v1.0 - 初始版本

---

## 一、需求分析

### 1.1 业务需求

用户需要：
1. **导入固定题库**：将 `vault_sample/大模型应用开发初级.docx` 文件转换为固定题库并导入到 `ai_cert_exam` 课程中
2. **考试页面入口**：在考试页面添加通过固定题库进入考试的入口，使用户可以选择使用固定题集进行考试

### 1.2 现状评估

#### 已有基础设施

**后端脚本**：
- ✅ `convert_docx_to_json.py` - docx 转 json 脚本已存在
- ✅ `import_questions.py` - 题目导入脚本，支持 `--course-code` 和 `--question-set-code` 参数

**数据模型**：
- ✅ `QuestionSet` 模型 - 支持固定题集（fixed_question_ids 字段）
- ✅ `Question` 模型 - 支持 question_set_ids 字段
- ✅ `Course` 模型 - 课程模型，包含默认考试配置

**服务层**：
- ✅ `QuestionSetService` - 题集服务
- ✅ `ExamService.start_exam()` - 支持两种考试模式：
  - `extraction` - 动态抽取（按题型数量）
  - `fixed_set` - 使用固定题集

**API层**：
- ✅ `/api/exam/start` - 支持传入 question_set_id（固定题集模式）
- ❌ 缺少题集列表查询 API

**前端**：
- ✅ 考试页面 `/exam/page.tsx` - 当前只支持动态抽取模式
- ❌ 缺少固定题集选择入口

### 1.3 核心问题

| 问题 | 严重程度 | 影响 |
|------|---------|------|
| **无题集列表查询 API** | P1 | 前端无法获取课程下的固定题集列表 |
| **前端缺少固定题集入口** | P0 | 用户无法选择使用固定题集进行考试 |
| **缺少完整导入流程文档** | P2 | 需要记录导入固定题库的步骤 |

---

## 二、修改意图

### 2.1 业务目标

1. **导入固定题库**：
   - 使用 `convert_docx_to_json.py` 将 docx 文件转换为 JSON
   - 使用 `import_questions.py` 将 JSON 导入为固定题集到 ai_cert_exam 课程

2. **添加考试入口**：
   - 在考试页面添加固定题集选择功能
   - 用户可以选择使用固定题集或动态抽取模式进行考试

### 2.2 设计原则

1. **最小化改动**：在现有架构基础上增量添加，不重构核心逻辑
2. **向后兼容**：现有动态抽取模式保持可用
3. **用户体验优先**：清晰区分两种考试模式，界面简洁直观

---

## 三、技术方案

### 3.1 后端修改

#### Step 1: 添加题集列表查询 API

**文件**: `src/backend/app/api/question_sets.py`

新增端点：
```python
@router.get("/by-course/{course_id}")
def get_question_sets_by_course(
    course_id: str,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取指定课程的题集列表

    Args:
        course_id: 课程ID
        active_only: 是否只返回启用的题集
        db: 数据库会话

    Returns:
        List[dict]: 题集列表
    """
    question_sets = QuestionSetService.get_question_sets(db, course_id, active_only)

    return [{
        "id": qs.id,
        "code": qs.code,
        "name": qs.name,
        "description": qs.description,
        "total_questions": qs.total_questions,
        "is_active": qs.is_active,
        "created_at": qs.created_at.isoformat() if qs.created_at else None
    } for qs in question_sets]
```

### 3.2 前端修改

#### Step 1: 修改 API 客户端

**文件**: `src/frontend/lib/api.ts`

添加题集相关接口：
```typescript
export interface QuestionSet {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  total_questions: number;
  is_active: boolean;
  created_at: string;
}

// 添加获取题集列表的方法
async getQuestionSetsByCourse(courseId: string): Promise<QuestionSet[]> {
  const response = await fetch(`${this.baseUrl}/question-sets/by-course/${courseId}`);
  if (!response.ok) throw new Error('Failed to fetch question sets');
  return response.json();
}
```

修改 `startExam` 方法，支持固定题集模式：
```typescript
async startExam(
  userId: string,
  totalQuestions: number = 50,
  difficultyRange?: number[],
  courseId?: string,
  questionSetCode?: string  // 新增参数：固定题集代码
) {
  const params = new URLSearchParams({
    user_id: userId,
    total_questions: totalQuestions.toString(),
  });

  if (courseId) params.append('course_id', courseId);
  if (questionSetCode) params.append('question_set_id', questionSetCode);  // 使用 question_set_id
  if (difficultyRange) params.append('difficulty_range', JSON.stringify(difficultyRange));

  const response = await fetch(`${this.baseUrl}/exam/start?${params}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to start exam');
  return response.json();
}
```

#### Step 2: 修改考试页面

**文件**: `src/frontend/app/exam/page.tsx`

在开始考试前添加题集选择功能：

```typescript
// 新增状态
const [examMode, setExamMode] = useState<'extraction' | 'fixed_set'>('extraction');
const [questionSets, setQuestionSets] = useState<any[]>([]);
const [selectedQuestionSet, setSelectedQuestionSet] = useState<string | null>(null);

// 获取题集列表
useEffect(() => {
  const fetchQuestionSets = async () => {
    const courseId = getCourseIdFromUrl();
    if (courseId) {
      try {
        const sets = await apiClient.getQuestionSetsByCourse(courseId);
        setQuestionSets(sets);
      } catch (error) {
        console.error('Failed to fetch question sets:', error);
      }
    }
  };
  fetchQuestionSets();
}, []);

// 修改 startExam 函数
const startExam = async () => {
  if (!userId) {
    alert('请先登录');
    window.location.href = '/';
    return;
  }

  setLoading(true);
  try {
    const courseId = getCourseIdFromUrl();
    const examData = await apiClient.startExam(
      userId,
      50,
      undefined,
      courseId || undefined,
      examMode === 'fixed_set' ? selectedQuestionSet || undefined : undefined
    );
    setExam(examData);
    const questionsData = await apiClient.getExamQuestions(userId, examData.exam_id, false);
    setQuestions(questionsData);
    setCurrentIndex(0);
    setCompleted(false);
    setShowAnswers(false);
  } catch (error) {
    console.error('Failed to start exam:', error);
    alert('开始考试失败');
  } finally {
    setLoading(false);
  }
};
```

在开始考试界面添加题集选择：
```tsx
{!exam && (
  <div className="text-center">
    <div className="bg-white rounded-lg shadow-md p-8 max-w-md mx-auto">
      <h2 className="text-2xl font-bold mb-4">开始考试</h2>

      {/* 考试模式选择 */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          选择考试模式
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => setExamMode('extraction')}
            className={`flex-1 py-2 px-4 rounded-lg ${
              examMode === 'extraction'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            动态抽取
          </button>
          <button
            onClick={() => setExamMode('fixed_set')}
            className={`flex-1 py-2 px-4 rounded-lg ${
              examMode === 'fixed_set'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            固定题集
          </button>
        </div>
      </div>

      {/* 固定题集选择 */}
      {examMode === 'fixed_set' && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            选择固定题集
          </label>
          {questionSets.length === 0 ? (
            <p className="text-gray-500 text-sm">
              当前课程暂无固定题集
            </p>
          ) : (
            <select
              value={selectedQuestionSet || ''}
              onChange={(e) => setSelectedQuestionSet(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg"
            >
              <option value="">请选择题集</option>
              {questionSets.map((qs) => (
                <option key={qs.id} value={qs.code}>
                  {qs.name} ({qs.total_questions} 题)
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      <p className="text-gray-700 mb-6">
        {examMode === 'extraction'
          ? '模拟真实考试环境，按题型数量随机抽取'
          : `使用固定题集进行考试，共 ${
              questionSets.find((qs) => qs.code === selectedQuestionSet)
                ?.total_questions || 0
            } 题`}
      </p>
      <button
        onClick={startExam}
        disabled={loading || (examMode === 'fixed_set' && !selectedQuestionSet)}
        className="w-full bg-purple-600 text-white py-3 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-lg"
      >
        {loading ? '加载中...' : '开始考试'}
      </button>
    </div>
  </div>
)}
```

### 3.3 导入流程

#### 完整导入步骤

**1. 运行 docx 转 json 脚本**：
```bash
cd src/scripts
uv run python convert_docx_to_json.py \
  -i ../vault_sample/大模型应用开发初级.docx \
  -o ../data/converted/大模型应用开发初级.json
```

**2. 导入为固定题集**：
```bash
cd src/scripts
uv run python import_questions.py \
  --json-file ../data/converted/大模型应用开发初级.json \
  --course-code ai_cert_exam \
  --question-set-code ai_cert_exam_fixed \
  --question-set-name "AI认证考试固定题集"
```

**3. 验证导入**：
```bash
# 查看题集列表
curl http://localhost:8000/api/question-sets/by-course/{course_id}
```

---

## 四、测试计划

### 4.1 导入测试

- [ ] docx 转 json 脚本成功执行
- [ ] JSON 文件格式正确
- [ ] 题目数量与 docx 中一致
- [ ] 导入脚本成功执行
- [ ] 固定题集创建成功
- [ ] 题目关联正确

### 4.2 前端测试

- [ ] 考试页面显示两种模式选项
- [ ] 选择"固定题集"模式后显示题集列表
- [ ] 题集显示名称和题目数量
- [ ] 选择题集后可以开始考试
- [ ] 动态抽取模式仍然可用
- [ ] 考试功能正常

### 4.3 集成测试

- [ ] 使用固定题集开始考试
- [ ] 考试题目数量与题集总数一致
- [ ] 考试流程正常
- [ ] 提交试卷后显示正确答案
- [ ] 分数计算正确

---

## 五、成功标准

### 功能完整性

- [ ] 固定题库成功导入到 ai_cert_exam 课程
- [ ] 考试页面显示固定题集选择入口
- [ ] 用户可以选择固定题集进行考试
- [ ] 动态抽取模式保持可用

### 用户体验

- [ ] 界面清晰：两种模式区分明显
- [ ] 操作简单：选择题集后即可开始考试
- [ ] 提示明确：未选择题集时禁用开始按钮

### 代码质量

- [ ] 遵循现有代码规范
- [ ] TypeScript 类型完整
- [ ] 中文注释完整
- [ ] 无 Lint 错误

---

## 六、时间估算

| 任务 | 预计工时 | 备注 |
|------|---------|------|
| 编写修改意图文档 | 0.5小时 | 本文档 |
| 导入固定题库（docx 转 json + 导入） | 0.5小时 | 使用现有脚本 |
| 添加题集列表查询 API | 0.5小时 | 新增 API 端点 |
| 修改 API 客户端 | 0.5小时 | 添加接口方法 |
| 修改考试页面 | 1小时 | 添加题集选择功能 |
| 测试与验证 | 1小时 | 功能测试 + 集成测试 |
| **总计** | **4小时** | |

---

**文档状态**: ✅ 准备就绪，可开始实施
**最后更新**: 2026-01-21
**版本**: v1.0
