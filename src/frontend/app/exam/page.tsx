'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient, Question, Course, User } from '@/lib/api';
import LaTeXRenderer from '@/components/LaTeXRenderer';
import Link from 'next/link';
import ThemeSelector from '@/components/ThemeSelector';

function ExamPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const courseId = searchParams.get('course_id');

  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [exam, setExam] = useState<{ exam_id: string; total_questions: number } | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [selectedOptions, setSelectedOptions] = useState<Set<string>>(new Set());

  const [examMode, setExamMode] = useState<'extraction' | 'fixed_set'>('extraction');
  const [questionSets, setQuestionSets] = useState<any[]>([]);
  const [selectedQuestionSet, setSelectedQuestionSet] = useState<string | null>(null);

  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      apiClient.getUser(savedUserId).then(setUser);
    } else {
      router.push('/');
    }
  }, [router]);

  useEffect(() => {
    if (!courseId) return;

    const fetchQuestionSets = async () => {
      try {
        const [sets, courseData] = await Promise.all([
          apiClient.getQuestionSets(courseId!, true),
          apiClient.getCourse(courseId!),
        ]);
        setQuestionSets(sets);
        setCourse(courseData);
        setLoading(false);
      } catch (error) {
        console.error('获取题集列表失败:', error);
        setLoading(false);
      }
    };
    fetchQuestionSets();
  }, [courseId]);

  const startExam = async () => {
    if (!user) {
      alert('请先登录');
      router.push('/');
      return;
    }

    setLoading(true);
    try {
      const examData = await apiClient.startExam(
        user.id,
        50,
        undefined,
        courseId || undefined,
        examMode === 'fixed_set' ? selectedQuestionSet || undefined : undefined
      );
      setExam(examData);
      const questionsData = await apiClient.getExamQuestions(user.id, examData.exam_id, false);
      setQuestions(questionsData);
      setCurrentIndex(0);
      setCompleted(false);
    } catch (error) {
      console.error('Failed to start exam:', error);
      alert('开始考试失败');
    } finally {
      setLoading(false);
    }
  };

  /**
   * 提交单题答案（考试模式）
   *
   * 业务逻辑说明：
   * - 考试模式下，只保存答案，不立即判断对错
   * - 提交成功后更新前端状态，标记该题已作答
   * - 提交过程中禁用按钮，防止重复提交
   * - 失败时提示用户，不阻塞后续操作
   *
   * @param questionId 题目ID
   * @param answer 用户选择的答案
   */
  const submitAnswer = async (questionId: string, answer: string) => {
    if (!user || !exam || submitting) return;

    setSubmitting(true);
    try {
      await apiClient.submitExamAnswer(user.id, exam.exam_id, questionId, answer);
      setQuestions(prev => prev.map(q =>
        q.id === questionId ? { ...q, user_answer: answer } : q
      ));
    } catch (error) {
      console.error('Failed to submit answer:', error);
      alert('提交答案失败');
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * 切换多选题选项选择
   *
   * 业务逻辑说明：
   * - 支持选项选择后可修改：如果题目已回答，从user_answer初始化selectedOptions
   * - 切换选项状态：已选则移除，未选则添加
   * - 更新前端状态，为提交答案做准备
   *
   * @param optionKey 选项键名（如A、B、C等）
   */
  const toggleOption = (optionKey: string) => {
    // 如果题目已回答且selectedOptions为空，从user_answer初始化
    const userAnswer = currentQuestion?.user_answer;
    if (userAnswer != null && selectedOptions.size === 0) {
      const existingOptions = userAnswer.split(',');
      setSelectedOptions(new Set(existingOptions));
      return;
    }

    const newSelected = new Set(selectedOptions);
    if (newSelected.has(optionKey)) {
      newSelected.delete(optionKey);
    } else {
      newSelected.add(optionKey);
    }
    setSelectedOptions(newSelected);
  };

  const submitMultipleChoiceAnswer = async () => {
    if (!currentQuestion) return;

    const sortedOptions = Array.from(selectedOptions).sort();
    const answer = sortedOptions.join(',');

    if (answer.length === 0) {
      alert('请至少选择一个选项');
      return;
    }

    await submitAnswer(currentQuestion.id, answer);
    setSelectedOptions(new Set());
  };

  const finishExam = async () => {
    if (!user || !exam) return;

    if (confirm('确认提交试卷？提交后将无法修改答案。')) {
      setSubmitting(true);
      try {
        await apiClient.finishExam(user.id, exam.exam_id);
        setCompleted(true);

        const questionsWithAnswers = await apiClient.getExamQuestions(user.id, exam.exam_id, true);
        setQuestions(questionsWithAnswers);
      } catch (error) {
        console.error('Failed to finish exam:', error);
        alert('提交试卷失败');
      } finally {
        setSubmitting(false);
      }
    }
  };

  const currentQuestion = questions[currentIndex];
  const allAnswered = questions.every(q => q.user_answer !== null);

  useEffect(() => {
    setSelectedOptions(new Set());
  }, [currentIndex]);

  if (loading && !exam) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--background)' }}>
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-2 rounded-full animate-spin" style={{ borderColor: 'var(--card-border)', borderTopColor: 'var(--primary)' }} />
          <p className="mt-4" style={{ color: 'var(--foreground-secondary)' }}>加载中...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--background)' }}>
        <div className="text-center max-w-md p-8" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
          <div className="w-14 h-14 mx-auto mb-4 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-md)' }}>
            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground-title)' }}>考试模式</h1>
          <p className="mb-6" style={{ color: 'var(--foreground-secondary)' }}>请先登录开始考试</p>
          <Link href="/courses" className="inline-block px-6 py-3 text-white font-medium" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-md)' }}>
            返回课程
          </Link>
        </div>
      </div>
    );
  }

  if (completed) {
    const correctCount = questions.filter(q => q.is_correct === true).length;
    const wrongCount = questions.filter(q => q.is_correct === false).length;
    const accuracy = questions.length > 0 ? Math.round((correctCount / questions.length) * 100) : 0;

    return (
      <div className="min-h-screen" style={{ background: 'var(--background)' }}>
        <nav className="sticky top-0 z-50 border-b" style={{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-14">
              <div className="flex items-center gap-2">
                <Link href="/" className="w-8 h-8 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-sm)' }}>
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </Link>
                {course && (
                  <>
                    <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
                    <span style={{ color: 'var(--foreground-title)' }}>{course.title}</span>
                    <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
                    <span style={{ color: 'var(--foreground-secondary)' }}>考试结果</span>
                  </>
                )}
              </div>
              <button onClick={() => router.push('/courses')} className="px-3 py-1.5 text-sm" style={{ background: 'var(--background-secondary)', color: 'var(--foreground-secondary)', borderRadius: 'var(--radius-sm)' }}>
                返回课程
              </button>
            </div>
          </div>
        </nav>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="p-6 mb-6" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
            <h2 className="text-2xl font-bold text-center mb-6" style={{ color: 'var(--foreground-title)' }}>考试完成</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
              <div className="p-4 text-center" style={{ background: 'var(--background-secondary)', borderRadius: 'var(--radius-md)' }}>
                <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>总题数</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--foreground-title)' }}>{questions.length}</p>
              </div>
              <div className="p-4 text-center" style={{ background: 'var(--primary-bg)', borderRadius: 'var(--radius-md)' }}>
                <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>正确率</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--primary)' }}>{accuracy}%</p>
              </div>
              <div className="p-4 text-center" style={{ background: 'var(--success-light)', borderRadius: 'var(--radius-md)' }}>
                <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>做对</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--success-dark)' }}>{correctCount}</p>
              </div>
              <div className="p-4 text-center" style={{ background: 'var(--error-light)', borderRadius: 'var(--radius-md)' }}>
                <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>做错</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--error-dark)' }}>{wrongCount}</p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {questions.map((q, index) => (
              <div
                key={q.id}
                className="p-6"
                style={{
                  background: 'var(--card-bg)',
                  border: `1px solid ${q.is_correct ? 'var(--success)' : 'var(--error)'}`,
                  borderRadius: 'var(--radius-lg)',
                }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className="px-2 py-1 text-xs" style={{ background: q.question_type === 'single_choice' ? 'var(--info-light)' : q.question_type === 'multiple_choice' ? 'var(--warning)' : 'var(--success-light)', color: q.question_type === 'single_choice' ? 'var(--info-dark)' : q.question_type === 'multiple_choice' ? '#fff' : 'var(--success-dark)', borderRadius: 'var(--radius-sm)' }}>
                    {q.question_type === 'single_choice' ? '单选题' : q.question_type === 'multiple_choice' ? '多选题' : '判断题'}
                  </span>
                  {q.question_set_codes && q.question_set_codes.length > 0 && (
                    <span className="px-2 py-1 text-xs" style={{ background: 'var(--background-secondary)', color: 'var(--foreground-secondary)', borderRadius: 'var(--radius-sm)' }}>
                      {q.question_set_codes.join(', ')}
                    </span>
                  )}
                  <span className={`text-sm font-medium ${q.is_correct ? 'text-green-600' : 'text-red-600'}`}>
                    {q.is_correct ? '✓ 正确' : '✗ 错误'}
                  </span>
                </div>

                <p className="font-medium mb-3" style={{ color: 'var(--foreground-title)' }}>{index + 1}. <LaTeXRenderer content={q.content} /></p>

                {q.question_type === 'multiple_choice' && q.user_answer != null && (
                  <div className="mb-3 p-3 text-sm" style={{ background: 'var(--info-light)', color: 'var(--info-dark)', borderRadius: 'var(--radius-sm)' }}>
                    <span className="font-semibold">你的选项：{q.user_answer}</span>
                    <span className="mx-2" style={{ color: 'var(--foreground-tertiary)' }}>|</span>
                    <span className="font-semibold">正确答案：{q.correct_answer}</span>
                  </div>
                )}

                {q.options && (
                  <div className="space-y-2 mb-4">
                    {Object.entries(q.options).map(([key, value]) => {
                      const isUserAnswer = q.user_answer?.includes(key);
                      const isCorrectAnswer = q.correct_answer?.includes(key);
                      return (
                        <div
                          key={key}
                          className="p-3"
                          style={{
                            background: isUserAnswer ? 'var(--primary-bg)' : 'var(--background-secondary)',
                            border: isUserAnswer ? '1px solid var(--primary)' : 'none',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          <strong style={{ color: 'var(--foreground-title)' }}>{key}.</strong>{' '}
                          <span style={{ color: 'var(--foreground-title)' }}><LaTeXRenderer content={value} /></span>
                          {isCorrectAnswer && <span className="ml-2 font-bold" style={{ color: 'var(--success)' }}>✓ 正确</span>}
                          {isUserAnswer && !isCorrectAnswer && <span className="ml-2 font-bold" style={{ color: 'var(--error)' }}>✗ 错误</span>}
                        </div>
                      );
                    })}
                  </div>
                )}

                {q.explanation && (
                  <div className="p-3" style={{ background: 'var(--background-secondary)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-sm)' }}>
                    <strong style={{ color: 'var(--foreground-title)' }}>解析:</strong>
                    <p className="mt-1" style={{ color: 'var(--foreground)' }}><LaTeXRenderer content={q.explanation} /></p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!exam) {
    return (
      <div className="min-h-screen" style={{ background: 'var(--background)' }}>
        <nav className="sticky top-0 z-50 border-b" style={{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-14">
              <div className="flex items-center gap-2">
                <Link href="/" className="w-8 h-8 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-sm)' }}>
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </Link>
                {course && (
                  <>
                    <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
                    <span style={{ color: 'var(--foreground-title)' }}>{course.title}</span>
                    <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
                    <span style={{ color: 'var(--foreground-secondary)' }}>考试模式</span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-3">
                <ThemeSelector />
                <button onClick={() => router.push('/courses')} className="px-3 py-1.5 text-sm" style={{ background: 'var(--background-secondary)', color: 'var(--foreground-secondary)', borderRadius: 'var(--radius-sm)' }}>
                  返回课程
                </button>
              </div>
            </div>
          </div>
        </nav>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <div className="max-w-md mx-auto p-8" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
              <div className="w-16 h-16 mx-auto mb-4 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-md)' }}>
                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--foreground-title)' }}>开始考试</h2>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2 text-left" style={{ color: 'var(--foreground-secondary)' }}>选择考试模式</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setExamMode('extraction')}
                    className="flex-1 py-2.5 px-4 font-medium transition-all"
                    style={examMode === 'extraction' ? { background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', color: '#fff', borderRadius: 'var(--radius-md)' } : { background: 'var(--background-secondary)', color: 'var(--foreground)', borderRadius: 'var(--radius-md)' }}
                  >
                    动态抽取
                  </button>
                  <button
                    onClick={() => setExamMode('fixed_set')}
                    className="flex-1 py-2.5 px-4 font-medium transition-all"
                    style={examMode === 'fixed_set' ? { background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', color: '#fff', borderRadius: 'var(--radius-md)' } : { background: 'var(--background-secondary)', color: 'var(--foreground)', borderRadius: 'var(--radius-md)' }}
                  >
                    固定题集
                  </button>
                </div>
              </div>

              {examMode === 'fixed_set' && (
                <div className="mb-6">
                  <label className="block text-sm font-medium mb-2 text-left" style={{ color: 'var(--foreground-secondary)' }}>选择固定题集</label>
                  {questionSets.length === 0 ? (
                    <p className="text-sm py-2" style={{ color: 'var(--foreground-tertiary)' }}>当前课程暂无固定题集</p>
                  ) : (
                    <select
                      value={selectedQuestionSet || ''}
                      onChange={(e) => setSelectedQuestionSet(e.target.value)}
                      className="w-full p-3 border"
                      style={{ color: 'var(--foreground)', borderColor: 'var(--card-border)', background: 'var(--background)', borderRadius: 'var(--radius-md)' }}
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

              <p className="mb-6 text-sm text-left" style={{ color: 'var(--foreground-secondary)' }}>
                {examMode === 'extraction'
                  ? '模拟真实考试环境，按题型数量随机抽取'
                  : `使用固定题集进行考试，共 ${questionSets.find((qs) => qs.code === selectedQuestionSet)?.total_questions || 0} 题`}
              </p>

              <button
                onClick={startExam}
                disabled={loading || (examMode === 'fixed_set' && !selectedQuestionSet)}
                className="w-full py-3 font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-md)' }}
              >
                {loading ? '加载中...' : '开始考试'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--background)' }}>
      <nav className="sticky top-0 z-50 border-b" style={{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-14">
            <div className="flex items-center gap-2">
              <Link href="/" className="w-8 h-8 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-sm)' }}>
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </Link>
              {course && (
                <>
                  <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
                  <Link href="/courses" style={{ color: 'var(--foreground-title)' }}>{course.title}</Link>
                  <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
                  <span style={{ color: 'var(--foreground-secondary)' }}>考试模式</span>
                </>
              )}
            </div>
            <div className="flex items-center gap-3">
              <ThemeSelector />
              <button onClick={() => router.push('/courses')} className="px-3 py-1.5 text-sm" style={{ background: 'var(--background-secondary)', color: 'var(--foreground-secondary)', borderRadius: 'var(--radius-sm)' }}>
                返回课程
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentQuestion && (
          <div className="p-6" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 text-sm font-semibold text-white" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-full)' }}>
                  {currentIndex + 1} / {questions.length}
                </span>
                <span className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>
                  {questions.filter(q => q.user_answer !== null).length} 题已答
                </span>
              </div>
              <div className="h-2 w-32 rounded-full overflow-hidden" style={{ background: 'var(--background-tertiary)' }}>
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${((currentIndex + 1) / questions.length) * 100}%`, background: 'linear-gradient(90deg, var(--primary), var(--primary-light))' }}
                />
              </div>
            </div>

            <div className="flex items-center gap-2 mb-4">
              <span className="px-2 py-1 text-xs" style={{ background: currentQuestion.question_type === 'single_choice' ? 'var(--info-light)' : currentQuestion.question_type === 'multiple_choice' ? 'var(--warning)' : 'var(--success-light)', color: currentQuestion.question_type === 'single_choice' ? 'var(--info-dark)' : currentQuestion.question_type === 'multiple_choice' ? '#fff' : 'var(--success-dark)', borderRadius: 'var(--radius-sm)' }}>
                {currentQuestion.question_type === 'single_choice' ? '单选题' : currentQuestion.question_type === 'multiple_choice' ? '多选题' : '判断题'}
              </span>
              {currentQuestion.question_set_codes && currentQuestion.question_set_codes.length > 0 && (
                <span className="px-2 py-1 text-xs" style={{ background: 'var(--background-secondary)', color: 'var(--foreground-secondary)', borderRadius: 'var(--radius-sm)' }}>
                  {currentQuestion.question_set_codes.join(', ')}
                </span>
              )}
            </div>

            <h2 className="text-lg font-semibold mb-6" style={{ color: 'var(--foreground-title)' }}>
              <LaTeXRenderer content={currentQuestion.content} />
            </h2>

            {currentQuestion.options && (
              <div className="space-y-3">
                {currentQuestion.question_type === 'multiple_choice' ? (
                  Object.entries(currentQuestion.options).map(([key, value]) => {
                    const isSelected = selectedOptions.has(key) || (currentQuestion.user_answer?.includes(key) && selectedOptions.size === 0);
                    return (
                      <button
                        key={key}
                        onClick={() => toggleOption(key)}
                        disabled={submitting}
                        className="w-full text-left p-4 transition-all disabled:opacity-50"
                        style={{
                          border: isSelected ? '2px solid var(--primary)' : '1px solid var(--card-border)',
                          background: isSelected ? 'var(--primary-bg)' : 'var(--background)',
                          borderRadius: 'var(--radius-md)',
                        }}
                      >
                        <strong style={{ color: isSelected ? 'var(--primary)' : 'var(--foreground-title)' }}>{key}.</strong>{' '}
                        <span style={{ color: 'var(--foreground-title)' }}><LaTeXRenderer content={value} /></span>
                        {isSelected && <span className="ml-2 font-bold" style={{ color: 'var(--primary)' }}>✓</span>}
                      </button>
                    );
                  })
                ) : (
                  Object.entries(currentQuestion.options).map(([key, value]) => (
                    <button
                      key={key}
                      onClick={() => submitAnswer(currentQuestion.id, key)}
                      disabled={submitting}
                      className="w-full text-left p-4 transition-all disabled:opacity-50"
                      style={{
                        border: currentQuestion.user_answer === key ? '2px solid var(--primary)' : '1px solid var(--card-border)',
                        background: currentQuestion.user_answer === key ? 'var(--primary-bg)' : 'var(--background)',
                        borderRadius: 'var(--radius-md)',
                      }}
                    >
                      <strong style={{ color: currentQuestion.user_answer === key ? 'var(--primary)' : 'var(--foreground-title)' }}>{key}.</strong>{' '}
                      <span style={{ color: 'var(--foreground-title)' }}><LaTeXRenderer content={value} /></span>
                      {currentQuestion.user_answer === key && <span className="ml-2 font-bold" style={{ color: 'var(--primary)' }}>✓</span>}
                    </button>
                  ))
                )}
              </div>
            )}

            {currentQuestion.question_type === 'multiple_choice' && selectedOptions.size > 0 && (
              <button
                onClick={submitMultipleChoiceAnswer}
                disabled={submitting}
                className="w-full mt-4 py-3 font-semibold text-white disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, var(--success), #14B8A6)', borderRadius: 'var(--radius-md)' }}
              >
                {submitting ? '提交中...' : '提交答案'}
              </button>
            )}

            <div className="flex gap-4 mt-6">
              <button
                onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
                disabled={currentIndex === 0 || submitting}
                className="flex-1 py-3 font-medium disabled:opacity-50"
                style={{ background: 'var(--background-secondary)', color: 'var(--foreground)', borderRadius: 'var(--radius-md)' }}
              >
                上一题
              </button>
              {currentIndex === questions.length - 1 && allAnswered && (
                <button
                  onClick={finishExam}
                  disabled={submitting || completed}
                  className="flex-1 py-3 font-medium text-white disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, var(--success), #14B8A6)', borderRadius: 'var(--radius-md)' }}
                >
                  提交试卷
                </button>
              )}
              {currentIndex < questions.length - 1 && (
                <button
                  onClick={() => setCurrentIndex(currentIndex + 1)}
                  disabled={submitting}
                  className="flex-1 py-3 font-medium text-white disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-md)' }}
                >
                  下一题
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ExamPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--background)' }}><p style={{ color: 'var(--foreground-secondary)' }}>加载中...</p></div>}>
      <ExamPageContent />
    </Suspense>
  );
}
