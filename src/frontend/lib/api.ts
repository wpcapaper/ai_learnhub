// API Client
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: string;
  username: string;
  email: string;
  nickname?: string | null;
  is_temp_user: boolean;
  user_level?: string | null;
  total_study_time: number;
  created_at: string;
  last_login?: string | null;
}

export interface Course {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  course_type: string;
  cover_image?: string | null;
  default_exam_config?: ExamConfig | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  total_questions?: number;
  answered_questions?: number;
  current_round?: number;        // 当前轮次
  total_rounds_completed?: number;  // 已完成轮次数
}

// Learning course interfaces
export interface Chapter {
  id: string;
  course_id: string;
  title: string;
  sort_order: number;
}

export interface ChapterContent {
  id: string;
  course_id: string;
  title: string;
  content_markdown: string;
  sort_order: number;
  course_code?: string;
  course_dir_name?: string;
  file_path?: string;
  user_progress?: UserProgress;
}

export interface UserProgress {
  last_position: number;
  last_percentage: number;
  is_completed: boolean;
  last_read_at?: string | null;
  total_read_time: number;
}

export interface ChapterProgressUpdate {
  position: number;
  percentage: number;
}

export interface LearningProgressSummary {
  course_id: string;
  course_title: string;
  total_chapters: number;
  completed_chapters: number;
  progress_percentage: number;
}


export interface QuestionSet {
  id: string;
  course_id: string;
  code: string;
  name: string;
  description?: string | null;
  total_questions: number;
  is_active: boolean;
  created_at: string;
}

export interface ExamConfig {
  question_type_config: {
    single_choice: number;
    multiple_choice: number;
    true_false: number;
  };
  difficulty_range: [number, number];
}

export interface Question {
  id: string;
  content: string;
  question_type: string;
  options?: Record<string, string> | string[] | null;
  correct_answer?: string | null;
  answer?: string | null;
  explanation?: string | null;
  user_answer?: string | null;
  is_correct?: boolean | null;
  answered_at?: string | null;
  question_set_codes?: string[];  // 题目所属的固定题集名称列表
  course?: {
    id: string;
    title: string;
  };
  difficulty?: number;
  last_wrong_time?: string | null;  // 最近的做错时间
}

export interface Batch {
  id: string;
  user_id: string;
  batch_size: number;
  mode: string;
  started_at: string;
  completed_at?: string | null;
  status: string;
}

export interface QuizResult {
  batch_id: string;
  total: number;
  correct: number;
  wrong: number;
  accuracy: number;
}

export interface UserStats {
  total_answered: number;
  correct_count: number;
  accuracy: number;
  mastered_count: number;
  due_review_count: number;
}

export interface ReviewStats {
  due_count: number;
  mastered_count: number;
}

export interface WordcloudStatus {
  has_wordcloud: boolean;
  generated_at?: string | null;
  words_count: number;
}

export interface WordcloudData {
  version: string;
  generated_at: string;
  words: Array<{ word: string; weight: number }>;
  source_stats: {
    total_chars: number;
    unique_words: number;
    top_words_count: number;
    total_files?: number;
  };
}

export interface AnswerSubmission {
  question_id: string;
  answer: string;
  is_correct: boolean;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<T>;
  }

  // User APIs
  async createUser(nickname?: string, userId?: string): Promise<User> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    return this.fetchJson<User>('/api/users/', {
      method: 'POST',
      body: JSON.stringify({ nickname }),
    });
  }

  async getUser(userId: string): Promise<User> {
    return this.fetchJson<User>(`/api/users/${userId}`);
  }

  async getUserStats(userId: string): Promise<UserStats> {
    return this.fetchJson<UserStats>(`/api/users/${userId}/stats`);
  }

  async listUsers(): Promise<User[]> {
    return this.fetchJson<User[]>('/api/users/');
  }

  async resetUserData(userId: string): Promise<{ message: string }> {
    return this.fetchJson<{ message: string }>(`/api/users/${userId}/reset`, {
      method: 'POST',
    });
  }

  // Review APIs
  async getNextQuestions(userId: string, courseId: string, batchSize = 10, allowNewRound = true): Promise<Question[]> {
    return this.fetchJson<Question[]>(`/api/review/next?user_id=${userId}&course_id=${courseId}&batch_size=${batchSize}&allow_new_round=${allowNewRound}`);
  }

  async submitAnswer(userId: string, submission: AnswerSubmission): Promise<{ record_id: string; review_stage: number; next_review_time?: string; message: string }> {
    return this.fetchJson<{ record_id: string; review_stage: number; next_review_time?: string; message: string }>('/api/review/submit', {
      method: 'POST',
      body: JSON.stringify({ ...submission, user_id: userId }),
    });
  }

  async getReviewStats(userId: string): Promise<ReviewStats> {
    return this.fetchJson<ReviewStats>(`/api/review/stats?user_id=${userId}`);
  }

  async getReviewQueue(userId: string, limit = 100): Promise<Array<{ question: Question; record: { id: string; is_correct: boolean | null; review_stage: number; next_review_time?: string; answered_at?: string | null } }>> {
    return this.fetchJson<Array<{ question: Question; record: any }>>(`/api/review/queue?user_id=${userId}&limit=${limit}`);
  }

  // Quiz APIs
  async startBatch(userId: string, mode = 'practice', batchSize = 10, courseId?: string): Promise<Batch> {
    return this.fetchJson<Batch>(`/api/quiz/start?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ mode, batch_size: batchSize, course_id: courseId }),
    });
  }

  async submitBatchAnswer(userId: string, batchId: string, questionId: string, answer: string): Promise<{ answer_id: string; question_id: string; user_answer: string; answered_at?: string | null }> {
    return this.fetchJson<{ answer_id: string; question_id: string; user_answer: string; answered_at?: string | null }>(`/api/quiz/${batchId}/answer?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, answer }),
    });
  }

  async finishBatch(userId: string, batchId: string): Promise<QuizResult> {
    return this.fetchJson<QuizResult>(`/api/quiz/${batchId}/finish?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async getBatchQuestions(userId: string, batchId: string): Promise<Question[]> {
    return this.fetchJson<Question[]>(`/api/quiz/${batchId}/questions?user_id=${userId}`);
  }

  async listBatches(userId: string, limit = 50): Promise<Batch[]> {
    return this.fetchJson<Batch[]>(`/api/quiz/batches?user_id=${userId}&limit=${limit}`);
  }

  async getBatch(userId: string, batchId: string): Promise<Batch> {
    return this.fetchJson<Batch>(`/api/quiz/${batchId}?user_id=${userId}`);
  }

  // Exam APIs
  /**
   * 开始考试
   * @param userId 用户ID
   * @param totalQuestions 总题目数（动态抽取模式使用）
   * @param difficultyRange 难度范围（动态抽取模式使用）
   * @param courseId 课程ID（必需）
   * @param questionSetCode 固定题集代码（使用固定题集模式时传入）
   */
  async startExam(
    userId: string,
    totalQuestions = 50,
    difficultyRange?: number[],
    courseId?: string,
    questionSetCode?: string
  ): Promise<{ exam_id: string; total_questions: number; mode: string; started_at: string; status: string }> {
    const params = new URLSearchParams({ user_id: userId });
    const body: any = { total_questions: totalQuestions };
    if (difficultyRange) body.difficulty_range = difficultyRange;
    if (courseId) body.course_id = courseId;
    // 使用 question_set_id 参数传递题集代码（后端通过 code 查找题集）
    if (questionSetCode) body.question_set_id = questionSetCode;
    return this.fetchJson<{ exam_id: string; total_questions: number; mode: string; started_at: string; status: string }>(`/api/exam/start?${params.toString()}`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  /**
   * 提交考试中的单题答案
   * @param userId 用户ID（必需，用于身份验证和数据隔离）
   * @param examId 考试ID
   * @param questionId 题目ID
   * @param answer 用户选择的答案
   * @returns 提交的答案信息
   */
  async submitExamAnswer(userId: string, examId: string, questionId: string, answer: string): Promise<{ answer_id: string; question_id: string; user_answer: string; answered_at?: string | null }> {
    // 重要：user_id 作为查询参数传递，后端通过查询参数获取用户身份
    // 与练习模式保持一致的参数传递方式
    return this.fetchJson<{ answer_id: string; question_id: string; user_answer: string; answered_at?: string | null }>(`/api/exam/${examId}/answer?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, answer }),
    });
  }

  /**
   * 提交考试（完成考试）
   * @param userId 用户ID（必需，作为查询参数传递）
   * @param examId 考试ID
   * @returns 考试结果
   */
  async finishExam(userId: string, examId: string): Promise<{ batch_id: string; total: number; correct: number; wrong: number; score: number }> {
    // 重要：user_id 作为查询参数传递（与练习模式保持一致）
    // 后端通过查询参数获取用户身份，而不是从请求体获取
    return this.fetchJson<{ batch_id: string; total: number; correct: number; wrong: number; score: number }>(`/api/exam/${examId}/finish?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async getExamQuestions(userId: string, examId: string, showAnswers = false): Promise<Question[]> {
    return this.fetchJson<Question[]>(`/api/exam/${examId}/questions?user_id=${userId}&show_answers=${showAnswers}`);
  }

  // Courses APIs
  async getCourses(activeOnly?: boolean, userId?: string): Promise<Course[]> {
    const params = new URLSearchParams();
    params.append('active_only', String(activeOnly ?? true));
    if (userId) params.append('user_id', userId);
    return this.fetchJson<Course[]>(`/api/courses/?${params.toString()}`);
  }

  async getCourse(courseId: string): Promise<Course> {
    return this.fetchJson<Course>(`/api/courses/${courseId}`);
  }

  // QuestionSets APIs
  async getQuestionSets(courseId: string, activeOnly?: boolean): Promise<QuestionSet[]> {
    return this.fetchJson<QuestionSet[]>(`/api/question-sets/?course_id=${courseId}&active_only=${activeOnly ?? true}`);
  }

  async getQuestionSetQuestions(setCode: string): Promise<Question[]> {
    return this.fetchJson<Question[]>(`/api/question-sets/${setCode}/questions`);
  }

  // Mistakes APIs
  async getMistakes(userId: string, courseId?: string): Promise<Question[]> {
    const params = new URLSearchParams();
    params.append('user_id', userId);
    if (courseId) params.append('course_id', courseId);
    return this.fetchJson<Question[]>(`/api/mistakes/?${params.toString()}`);
  }

  // Learning Course APIs
  async getLearningChapters(courseId: string): Promise<Chapter[]> {
    return this.fetchJson<Chapter[]>(`/api/learning/${courseId}/chapters`);
  }

  async getChapterContent(chapterId: string, userId?: string): Promise<ChapterContent> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    return this.fetchJson<ChapterContent>(`/api/learning/${chapterId}/content?${params.toString()}`);
  }

  async updateReadingProgress(chapterId: string, userId: string, progress: ChapterProgressUpdate): Promise<UserProgress> {
    return this.fetchJson<UserProgress>(`/api/learning/${chapterId}/progress?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify(progress),
    });
  }

  async markChapterCompleted(chapterId: string, userId: string): Promise<UserProgress> {
    return this.fetchJson<UserProgress>(`/api/learning/${chapterId}/complete?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async getLearningProgress(courseId: string, userId: string): Promise<LearningProgressSummary> {
    return this.fetchJson<LearningProgressSummary>(`/api/learning/${courseId}/progress?user_id=${userId}`);
  }

  // 词云 API
  async getCourseWordcloudStatus(courseId: string): Promise<WordcloudStatus> {
    return this.fetchJson<WordcloudStatus>(`/api/admin/courses/${courseId}/wordcloud/status`);
  }

  async getCourseWordcloud(courseId: string): Promise<WordcloudData> {
    return this.fetchJson<WordcloudData>(`/api/admin/courses/${courseId}/wordcloud`);
  }

  async getChapterWordcloud(courseId: string, chapterName: string): Promise<WordcloudData> {
    return this.fetchJson<WordcloudData>(`/api/admin/courses/${courseId}/chapters/${chapterName}/wordcloud`);
  }

  // AI 对话 API（流式响应）
  async aiChatStream(chapterId: string, message: string, userId?: string): Promise<ReadableStream<string>> {
    const body: any = { chapter_id: chapterId, message };
    if (userId) body.user_id = userId;

    const response = await fetch(`${this.baseUrl}/api/learning/ai/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`AI Chat Error: ${response.status} ${response.statusText}`);
    }

    return response.body as unknown as ReadableStream<string>;
  }


  async getMistakesStats(userId: string, courseId?: string): Promise<{ total_wrong: number; wrong_by_course: Record<string, number>; wrong_by_type: Record<string, number> }> {
    const params = new URLSearchParams();
    params.append('user_id', userId);
    if (courseId) params.append('course_id', courseId);
    return this.fetchJson<{ total_wrong: number; wrong_by_course: Record<string, number>; wrong_by_type: Record<string, number> }>(`/api/mistakes/stats?${params.toString()}`);
  }

  async retryMistakes(userId: string, courseId?: string, batchSize = 10): Promise<{ batch_id: string; questions: Question[] }> {
    const params: any = { user_id: userId, batch_size: batchSize };
    if (courseId) params.course_id = courseId;
    return this.fetchJson<{ batch_id: string; questions: Question[] }>('/api/mistakes/retry', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async retryMistakesExam(userId: string, courseId?: string): Promise<{ exam_id: string; total_questions: number; mode: string; started_at: string; status: string }> {
    const body: any = { user_id: userId };
    if (courseId) body.course_id = courseId;
    return this.fetchJson<{ exam_id: string; total_questions: number; mode: string; started_at: string; status: string }>('/api/mistakes/retry-exam', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // 新增：全部错题重练API
  async retryAllMistakes(userId: string, courseId?: string): Promise<{ batch_id: string; questions: Question[]; total_count: number }> {
    const body: any = { user_id: userId };
    if (courseId) body.course_id = courseId;
    return this.fetchJson<{ batch_id: string; questions: Question[]; total_count: number }>('/api/mistakes/retry-all', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }
}

export const apiClient = new ApiClient();
