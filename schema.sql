-- ========================================
-- AILearn Hub 数据库 Schema
-- 基于 SQLite 设计（PostgreSQL 兼容）
-- ========================================

-- ========================================
-- 表：用户 (users)
-- 说明：用户基本信息，支持 Dev 模式（临时用户）和生产模式（注册用户）
-- ========================================
CREATE TABLE users (
    -- 主键：用户唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 用户名：唯一，用于登录和显示
    username TEXT NOT NULL UNIQUE,

    -- 邮箱：唯一，用户联系信息
    email TEXT NOT NULL UNIQUE,

    -- 密码哈希：加密后的用户密码
    password_hash TEXT NOT NULL,

    -- 昵称：用户显示名称（可选）
    nickname TEXT,

    -- 是否临时用户：标识是否为 Dev 模式下的临时用户
    is_temp_user BOOLEAN DEFAULT 0 NOT NULL,

    -- 总学习时间：累计学习时长（单位：秒）
    total_study_time INTEGER DEFAULT 0 NOT NULL,

    -- 用户等级：用户学习等级（beginner | intermediate | advanced）
    user_level TEXT,

    -- 创建时间：用户账号创建时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 最后登录时间：用户最后一次登录的时间
    last_login TIMESTAMP,

    -- 是否已删除：软删除标记
    is_deleted BOOLEAN DEFAULT 0 NOT NULL
);

-- 索引：用户名索引 - 登录查询优化
CREATE INDEX idx_users_username ON users(username);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_users_1 ON users(id);


-- ========================================
-- 表：课程 (courses)
-- 说明：课程基本信息，支持考试和学习两种类型
-- ========================================
CREATE TABLE courses (
    -- 主键：课程唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 课程代码：唯一，用于课程标识和引用
    code TEXT NOT NULL UNIQUE,

    -- 课程标题：课程显示名称
    title TEXT NOT NULL,

    -- 课程描述：课程详细介绍
    description TEXT,

    -- 课程类型：exam（考试）| learning（学习）
    course_type TEXT NOT NULL,

    -- 封面图 URL：课程封面图片链接
    cover_image TEXT,

    -- 默认考试配置：系统级的考试配置（JSON 格式）
    -- 结构示例：
    -- {
    --   "question_type_config": {
    --     "single_choice": 30,
    --     "multiple_choice": 10,
    --     "true_false": 10
    --   },
    --   "difficulty_range": [1, 5]
    -- }
    default_exam_config TEXT,

    -- 是否启用：控制课程是否对用户可见
    is_active BOOLEAN DEFAULT 1 NOT NULL,

    -- 排序顺序：课程列表显示顺序
    sort_order INTEGER DEFAULT 0 NOT NULL,

    -- 创建时间：课程创建时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 是否已删除：软删除标记
    is_deleted BOOLEAN DEFAULT 0 NOT NULL
);

-- 索引：课程代码索引 - 快速查找课程
CREATE INDEX idx_courses_code ON courses(code);

-- 索引：课程类型索引 - 按类型筛选课程
CREATE INDEX idx_courses_course_type ON courses(course_type);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_courses_1 ON courses(id);


-- ========================================
-- 表：题集 (question_sets)
-- 说明：固定题集，包含预设的题目列表
-- ========================================
CREATE TABLE question_sets (
    -- 主键：题集唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 课程 ID：所属课程（外键关联）
    course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,

    -- 题集代码：唯一，用于题集标识
    code TEXT NOT NULL UNIQUE,

    -- 题集名称：题集显示名称
    name TEXT NOT NULL,

    -- 固定题目 ID 列表：该题集包含的题目 ID（JSON 数组格式）
    -- 示例：["q-uuid-1", "q-uuid-2", "q-uuid-3"]
    fixed_question_ids TEXT NOT NULL,

    -- 题集描述：题集详细介绍
    description TEXT,

    -- 题目总数：题集包含的题目数量
    total_questions INTEGER DEFAULT 0 NOT NULL,

    -- 是否启用：控制题集是否可用
    is_active BOOLEAN DEFAULT 1 NOT NULL,

    -- 创建时间：题集创建时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 是否已删除：软删除标记
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,

    -- 外键约束：课程 ID - 关联到 courses 表
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- 索引：课程 ID 索引 - 按课程查找题集
CREATE INDEX idx_question_sets_course_id ON question_sets(course_id);

-- 索引：题集代码索引 - 快速查找题集
CREATE INDEX idx_question_sets_code ON question_sets(code);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_question_sets_1 ON question_sets(id);


-- ========================================
-- 表：题目 (questions)
-- 说明：题目基本信息，支持多种题型
-- ========================================
CREATE TABLE questions (
    -- 主键：题目唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 课程 ID：所属课程（外键关联）
    course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,

    -- 题目类型：single_choice（单选题）| multiple_choice（多选题）| true_false（判断题）
    question_type TEXT NOT NULL,

    -- 题目内容：题目描述
    content TEXT NOT NULL,

    -- 选项：题目选项（JSON 格式）
    -- 示例：{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}
    options TEXT,

    -- 正确答案：标准答案
    correct_answer TEXT NOT NULL,

    -- 解析：题目详细解析
    explanation TEXT,

    -- 知识点：题目涉及的知识点列表（JSON 数组格式）
    -- 示例：["监督学习", "分类", "决策树"]
    knowledge_points TEXT,

    -- 难度：题目难度等级（1-5）
    difficulty INTEGER,

    -- 题集 ID 列表：题目所属的固定题集（JSON 数组格式）
    -- 示例：["qs-uuid-1", "qs-uuid-2"]
    question_set_ids TEXT DEFAULT '[]',

    -- 是否有争议：标记题目是否为争议题
    is_controversial BOOLEAN DEFAULT 0 NOT NULL,

    -- 额外数据：扩展数据（JSON 格式）
    extra_data TEXT DEFAULT '{}',

    -- 向量 ID：题目标题向量化后的 ID（用于语义搜索）
    vector_id TEXT,

    -- 创建时间：题目创建时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 是否已删除：软删除标记
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,

    -- 外键约束：课程 ID - 关联到 courses 表
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- 索引：课程 ID 索引 - 按课程查找题目
CREATE INDEX idx_questions_course_id ON questions(course_id);

-- 索引：题目类型索引 - 按类型筛选题目
CREATE INDEX idx_questions_question_type ON questions(question_type);

-- 索引：正确答案索引 - 按答案筛选题目
CREATE INDEX idx_questions_correct_answer ON questions(correct_answer);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_questions_1 ON questions(id);


-- ========================================
-- 表：用户设置 (user_settings)
-- 说明：用户个性化设置，主要为课程相关配置
-- ========================================
CREATE TABLE user_settings (
    -- 主键：设置唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 用户 ID：关联用户（外键）
    user_id TEXT NOT NULL UNIQUE,

    -- 课程设置：用户对各课程的个性化设置（JSON 格式）
    -- 结构示例：
    -- {
    --   "course-1": {
    --     "exam_config": {
    --       "question_type_config": {
    --         "single_choice": 20,
    --         "multiple_choice": 15,
    --         "true_false": 15
    --       },
    --       "difficulty_range": [2, 4]
    --     },
    --     "practice_mode": "sequential"
    --   }
    -- }
    course_settings TEXT DEFAULT '{}',

    -- 更新时间：设置最后更新时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 创建时间：设置创建时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引：用户 ID 索引 - 查找用户设置
CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_user_settings_1 ON user_settings(id);


-- ========================================
-- 表：用户课程进度 (user_course_progress)
-- 说明：跟踪用户在每个课程上的学习进度和轮次信息
-- ========================================
CREATE TABLE user_course_progress (
    -- 主键：进度记录唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 用户 ID：关联用户（外键）
    user_id TEXT NOT NULL,

    -- 课程 ID：关联课程（外键）
    course_id TEXT NOT NULL,

    -- 当前轮次：当前学习轮次，从 1 开始
    current_round INTEGER DEFAULT 1 NOT NULL,

    -- 已完成轮次数：用户已完成的轮次总数
    total_rounds_completed INTEGER DEFAULT 0 NOT NULL,

    -- 开始时间：第一次开始学习该课程的时间
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 更新时间：进度最后更新时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引：用户 ID 索引 - 查询用户的所有课程进度
CREATE INDEX idx_user_course_progress_user_id ON user_course_progress(user_id);

-- 索引：课程 ID 索引 - 查询某个课程的所有用户进度
CREATE INDEX idx_user_course_progress_course_id ON user_course_progress(course_id);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_user_course_progress_1 ON user_course_progress(id);


-- ========================================
-- 表：用户学习记录 (user_learning_records)
-- 说明：用户对每个题目的学习记录，包含艾宾浩斯复习算法的状态
-- ========================================
CREATE TABLE user_learning_records (
    -- 主键：学习记录唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 用户 ID：关联用户（外键）
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 题目 ID：关联题目（外键）
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,

    -- 复习阶段：艾宾浩斯复习阶段（0-7, 8=已掌握）
    -- 0: 新题
    -- 1-7: 复习阶段（对应不同复习间隔）
    -- 8: 已掌握
    review_stage INTEGER DEFAULT 0 NOT NULL,

    -- 下次复习时间：根据艾宾浩斯曲线计算的下次复习时间
    -- 答对的题目在复习队列中不在此字段记录
    next_review_time TIMESTAMP,

    -- 当前轮次是否完成：标记题目在当前轮次是否已刷过
    -- 独立于艾宾浩斯状态，用于轮次管理
    completed_in_current_round BOOLEAN DEFAULT 0 NOT NULL,

    -- 外键约束：用户 ID - 关联到 users 表
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    -- 外键约束：题目 ID - 关联到 questions 表
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- 索引：用户 ID 索引 - 查询用户的所有学习记录
CREATE INDEX idx_user_learning_records_user_id ON user_learning_records(user_id);

-- 索引：题目 ID 索引 - 查询某个题目的所有学习记录
CREATE INDEX idx_user_learning_records_question_id ON user_learning_records(question_id);

-- 索引：复习阶段索引 - 查询特定阶段的题目
CREATE INDEX idx_user_learning_records_review_stage ON user_learning_records(review_stage);

-- 索引：下次复习时间索引 - 复习调度查询
CREATE INDEX idx_user_learning_records_next_review_time ON user_learning_records(next_review_time);

-- 索引：当前轮次完成状态索引 - 轮次管理查询
CREATE INDEX idx_user_learning_records_completed_in_current_round ON user_learning_records(completed_in_current_round);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_user_learning_records_1 ON user_learning_records(id);


-- ========================================
-- 表：用户答题历史 (user_answer_history)
-- 说明：用户每次答题的完整历史记录，永不更新，用于追踪答题情况
-- ========================================
CREATE TABLE user_answer_history (
    -- 主键：答题历史记录唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 用户 ID：关联用户（外键）
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 题目 ID：关联题目（外键）
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,

    -- 用户答案：用户提交的答案（固定不变）
    answer TEXT NOT NULL,

    -- 是否正确：答题结果（固定不变）
    is_correct BOOLEAN NOT NULL,

    -- 答题时间：答题发生的时间
    answered_at TIMESTAMP NOT NULL,

    -- 答题时的复习阶段：记录答题时的复习阶段状态
    review_stage INTEGER NOT NULL,

    -- 批次 ID：关联答题批次（可选，外键）
    batch_id TEXT REFERENCES quiz_batches(id) ON DELETE SET NULL,

    -- 外键约束：用户 ID - 关联到 users 表
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    -- 外键约束：题目 ID - 关联到 questions 表
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,

    -- 外键约束：批次 ID - 关联到 quiz_batches 表
    FOREIGN KEY (batch_id) REFERENCES quiz_batches(id) ON DELETE SET NULL
);

-- 索引：用户 ID 索引 - 查询用户的所有答题历史
CREATE INDEX idx_user_answer_history_user_id ON user_answer_history(user_id);

-- 索引：题目 ID 索引 - 查询某个题目的所有答题历史
CREATE INDEX idx_user_answer_history_question_id ON user_answer_history(question_id);

-- 索引：答题时间索引 - 按时间查询答题历史
CREATE INDEX idx_user_answer_history_answered_at ON user_answer_history(answered_at);

-- 索引：批次 ID 索引 - 查询批次内的答题记录
CREATE INDEX idx_user_answer_history_batch_id ON user_answer_history(batch_id);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_user_answer_history_1 ON user_answer_history(id);


-- ========================================
-- 表：批次刷题 (quiz_batches)
-- 说明：用户每次刷题/考试的批次会话记录
-- ========================================
CREATE TABLE quiz_batches (
    -- 主键：批次唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 用户 ID：关联用户（外键）
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 批次大小：每批包含的题目数量
    batch_size INTEGER DEFAULT 10 NOT NULL,

    -- 模式：刷题模式（practice）| 考试模式（exam）
    mode TEXT DEFAULT 'practice' NOT NULL,

    -- 轮次编号：当前轮次编号，从 1 开始
    round_number INTEGER DEFAULT 1 NOT NULL,

    -- 开始时间：批次开始时间
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 完成时间：批次完成时间
    completed_at TIMESTAMP,

    -- 状态：进行中（in_progress）| 已完成（completed）
    status TEXT DEFAULT 'in_progress' NOT NULL,

    -- 是否已删除：软删除标记
    is_deleted BOOLEAN DEFAULT 0 NOT NULL,

    -- 外键约束：用户 ID - 关联到 users 表
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 索引：用户 ID 索引 - 查询用户的所有批次
CREATE INDEX idx_quiz_batches_user_id ON quiz_batches(user_id);

-- 索引：开始时间索引 - 按时间查询批次
CREATE INDEX idx_quiz_batches_started_at ON quiz_batches(started_at);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_quiz_batches_1 ON quiz_batches(id);


-- ========================================
-- 表：批次答题记录 (batch_answers)
-- 说明：批次中每个题目的答题记录
-- ========================================
CREATE TABLE batch_answers (
    -- 主键：批次答题记录唯一标识符
    id TEXT NOT NULL PRIMARY KEY,

    -- 批次 ID：关联批次（外键）
    batch_id TEXT NOT NULL REFERENCES quiz_batches(id) ON DELETE CASCADE,

    -- 题目 ID：关联题目（外键）
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,

    -- 用户答案：用户提交的答案
    user_answer TEXT,

    -- 是否正确：答题结果（批次结束后统一更新）
    is_correct BOOLEAN,

    -- 答题时间：答题发生的时间
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束：批次 ID - 关联到 quiz_batches 表
    FOREIGN KEY (batch_id) REFERENCES quiz_batches(id) ON DELETE CASCADE,

    -- 外键约束：题目 ID - 关联到 questions 表
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- 索引：批次 ID 索引 - 查询批次中的所有答题记录
CREATE INDEX idx_batch_answers_batch_id ON batch_answers(batch_id);

-- 索引：题目 ID 索引 - 查询某个题目在不同批次的答题记录
CREATE INDEX idx_batch_answers_question_id ON batch_answers(question_id);

-- 索引：主键索引 - SQLAlchemy 自动创建
-- CREATE UNIQUE INDEX sqlite_autoindex_batch_answers_1 ON batch_answers(id);


-- ========================================
-- 视图：用户学习统计（可选）
-- 说明：汇总用户的学习统计数据
-- ========================================
-- 注意：SQLite 视图不支持外键，此处仅为示例，实际使用可能需要调整
/*
CREATE VIEW user_learning_stats AS
SELECT
    u.id AS user_id,
    u.username,
    COUNT(DISTINCT uah.id) AS total_answers,
    SUM(CASE WHEN uah.is_correct = 1 THEN 1 ELSE 0 END) AS correct_answers,
    ROUND(
        CASE
            WHEN COUNT(DISTINCT uah.id) = 0 THEN 0
            ELSE CAST(SUM(CASE WHEN uah.is_correct = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(DISTINCT uah.id) * 100
        END,
        2
    ) AS accuracy_rate,
    COUNT(DISTINCT CASE WHEN ulr.review_stage = 8 THEN ulr.question_id END) AS mastered_count,
    COUNT(DISTINCT CASE WHEN ulr.next_review_time IS NOT NULL AND ulr.next_review_time <= datetime('now') THEN ulr.question_id END) AS pending_review_count
FROM
    users u
LEFT JOIN
    user_answer_history uah ON u.id = uah.user_id
LEFT JOIN
    user_learning_records ulr ON u.id = ulr.user_id
GROUP BY
    u.id;
*/


-- ========================================
-- 艾宾浩斯复习阶段说明
-- ========================================
-- 阶段 | 复习间隔 | 记忆保持率
-- -----|---------|-----------
-- 0    | 新题     | 100%
-- 1    | 30分钟   | 85%
-- 2    | 12小时   | 70%
-- 3    | 1天      | 60%
-- 4    | 2天      | 50%
-- 5    | 4天      | 40%
-- 6    | 7天      | 30%
-- 7    | 15天     | 20%
-- 8    | 已掌握   | -
--
-- 规则：
-- - 答对：进入下一阶段
-- - 答错：回到第1阶段重新开始
-- - 答对的题目不进入复习队列（next_review_time 为 NULL）
-- - 复习队列仅包含需要复习的题目（next_review_time 不为 NULL）
