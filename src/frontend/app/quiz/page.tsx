'use client';

/**
 * 刷题页面
 * 
 * 功能说明：
 * - 支持单选题和多选题答题
 * - 批次答题模式，完成后显示成绩
 * - Phase 3 Active Intervention：连续答错3题后建议 AI 诊断
 */

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient, Question, Course, User, Batch } from '@/lib/api';
import LaTeXRenderer from '@/components/LaTeXRenderer';
import Link from 'next/link';
import ThemeSelector from '@/components/ThemeSelector';

// 连续答错阈值
const CONSECUTIVE_WRONG_THRESHOLD = 3;

function QuizPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const courseId = searchParams.get('course_id');
  const batchIdParam = searchParams.get('batch_id');

  // 基础状态
  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [batch, setBatch] = useState<Batch | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState<{ correct: number; wrong: number; total: number } | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<Set<string>>(new Set());

  // Phase 3 Active Intervention 状态
  // 关键业务逻辑：连续答错3题后触发 AI 诊断建议
  const [consecutiveWrongCount, setConsecutiveWrongCount] = useState(0);
  const [showInterventionModal, setShowInterventionModal] = useState(false);

  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      apiClient.getUser(savedUserId).then(setUser);
    } else {
      router.push('/');
    }
  }, [router]);

  useEffect(() => {
    if (!user) return;

    const loadQuiz = async () => {
      try {
        // 如果有 batch_id 参数，直接加载已有批次（用于错题重练）
        if (batchIdParam) {
          const batchData = await apiClient.getBatch(user.id, batchIdParam);
          setBatch(batchData);
          
          const questionsData = await apiClient.getBatchQuestions(user.id, batchIdParam);
          setQuestions(questionsData);
          
          if (batchData.course_id) {
            const courseData = await apiClient.getCourse(batchData.course_id);
            setCourse(courseData);
          }
          
          setLoading(false);
          
          if (questionsData.length === 0) {
            alert('暂无题目可刷');
            router.push('/courses');
          }
          return;
        }

        // 否则创建新批次
        if (!courseId) {
          router.push('/courses');
          return;
        }

        const courseData = await apiClient.getCourse(courseId);
        setCourse(courseData);

        const batchData = await apiClient.startBatch(user.id, 'practice', 10, courseId);
        setBatch(batchData);

        const questionsData = await apiClient.getBatchQuestions(user.id, batchData.id);
        setQuestions(questionsData);
        setLoading(false);

        if (questionsData.length === 0) {
          alert('暂无题目可刷');
          router.push('/courses');
        }
      } catch (err) {
        console.error('Failed to load quiz:', err);
        setLoading(false);
      }
    };

    loadQuiz();
  }, [user, courseId, batchIdParam, router]);

  const currentQuestion = questions[currentIndex];

  /**
   * 提交单题答案（练习模式）
   *
   * 业务逻辑说明：
   * - 练习模式下，只保存答案，不立即判断对错
   * - 提交成功后更新前端状态，标记该题已作答
   * - 提交过程中禁用按钮，防止重复提交
   * - 失败时提示用户，不阻塞后续操作
   *
   * @param questionId 题目ID
   * @param answer 用户选择的答案
   */
  const submitAnswer = async (questionId: string, answer: string) => {
    if (!user || !batch || submitting) return;

    setSubmitting(true);
    try {
      await apiClient.submitBatchAnswer(user.id, batch.id, questionId, answer);
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

  /**
   * 处理刷题完成
   *
   * 业务逻辑说明：
   * - 完成批次后检查连续错误情况
   * - 如果连续答错达到阈值，弹出 AI 诊断建议
   */
  const finishBatch = async () => {
    if (!user || !batch) return;

    const allAnswered = questions.every(q => q.user_answer !== null);
    if (!allAnswered) {
      alert('请先回答所有题目');
      return;
    }

    setSubmitting(true);
    try {
      const quizResult = await apiClient.finishBatch(user.id, batch.id);
      setResult({ correct: quizResult.correct, wrong: quizResult.wrong, total: quizResult.total });

      const questionsWithAnswers = await apiClient.getBatchQuestions(user.id, batch.id);
      setQuestions(questionsWithAnswers);
      setCompleted(true);
      
      // Phase 3: 检测连续错误
      // 关键业务逻辑：检查是否有连续答错达到阈值的情况
      let maxConsecutive = 0;
      let currentConsecutive = 0;
      for (const q of questionsWithAnswers) {
        if (!q.is_correct) {
          currentConsecutive++;
          maxConsecutive = Math.max(maxConsecutive, currentConsecutive);
        } else {
          currentConsecutive = 0;
        }
      }
      setConsecutiveWrongCount(maxConsecutive);
      
      // 如果连续答错达到阈值，显示干预弹窗
      if (maxConsecutive >= CONSECUTIVE_WRONG_THRESHOLD) {
        setShowInterventionModal(true);
      }
    } catch (error) {
      console.error('Failed to finish batch:', error);
      alert('提交失败');
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    setSelectedOptions(new Set());
  }, [currentIndex]);

  if (loading) {
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
          <p className="mb-4" style={{ color: 'var(--foreground-secondary)' }}>请先登录</p>
          <Link href="/" className="inline-block px-6 py-2 text-white" style={{ background: 'var(--primary)', borderRadius: 'var(--radius-md)' }}>返回首页</Link>
        </div>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--background)' }}>
        <div className="text-center max-w-md p-8" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
          <p className="mb-4" style={{ color: 'var(--foreground-secondary)' }}>暂无待刷题目</p>
          <button onClick={() => router.push('/courses')} className="px-6 py-2 text-white" style={{ background: 'var(--primary)', borderRadius: 'var(--radius-md)' }}>返回课程</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--background)' }}>
      {/* 导航栏 */}
      <nav className="sticky top-0 z-50 border-b" style={{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-14">
            <div className="flex items-center gap-2">
              <Link href="/" className="w-8 h-8 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-sm)' }}>
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </Link>
              <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
              <Link href="/courses" style={{ color: 'var(--foreground-title)' }}>选择课程</Link>
              {course && (
                <>
                  <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
                  <span style={{ color: 'var(--foreground-secondary)' }}>{course.title}</span>
                </>
              )}
              <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
              <span style={{ color: 'var(--primary)' }}>刷题</span>
            </div>
            <div className="flex items-center gap-3">
              <ThemeSelector />
              <button onClick={() => router.push('/courses')} className="px-3 py-1.5 text-sm" style={{ background: 'var(--background-secondary)', color: 'var(--foreground-secondary)', borderRadius: 'var(--radius-sm)' }}>返回课程</button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 完成状态 */}
        {completed && result ? (
          <div className="p-6" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
            <h2 className="text-2xl font-bold text-center mb-6" style={{ color: 'var(--foreground-title)' }}>刷题完成</h2>
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="p-4 text-center" style={{ background: 'var(--background-secondary)', borderRadius: 'var(--radius-md)' }}>
                <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>总题数</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--foreground-title)' }}>{result.total}</p>
              </div>
              <div className="p-4 text-center" style={{ background: 'var(--success-light)', borderRadius: 'var(--radius-md)' }}>
                <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>正确</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--success-dark)' }}>{result.correct}</p>
              </div>
              <div className="p-4 text-center" style={{ background: 'var(--error-light)', borderRadius: 'var(--radius-md)' }}>
                <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>错误</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--error-dark)' }}>{result.wrong}</p>
              </div>
            </div>
            <div className="text-center mb-6">
              <p className="text-lg" style={{ color: 'var(--foreground-title)' }}>正确率: <strong style={{ color: 'var(--primary)' }}>{Math.round((result.correct / result.total) * 100)}%</strong></p>
            </div>

            {/* 题目列表 */}
            <div className="space-y-4 mb-6">
              {questions.map((q, index) => (
                <div
                  key={q.id}
                  className="p-4"
                  style={{
                    background: 'var(--background-secondary)',
                    border: `1px solid ${q.is_correct ? 'var(--success)' : 'var(--error)'}`,
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-1 text-xs" style={{ background: q.question_type === 'single_choice' ? 'var(--info-light)' : q.question_type === 'multiple_choice' ? 'var(--warning)' : 'var(--success-light)', color: q.question_type === 'single_choice' ? 'var(--info-dark)' : q.question_type === 'multiple_choice' ? '#fff' : 'var(--success-dark)', borderRadius: 'var(--radius-sm)' }}>
                      {q.question_type === 'single_choice' ? '单选题' : q.question_type === 'multiple_choice' ? '多选题' : '判断题'}
                    </span>
                    <span className="text-sm font-medium" style={{ color: q.is_correct ? 'var(--success)' : 'var(--error)' }}>
                      {q.is_correct ? '✓ 正确' : '✗ 错误'}
                    </span>
                  </div>
                  <p className="font-medium mb-2" style={{ color: 'var(--foreground-title)' }}>{index + 1}. <LaTeXRenderer content={q.content} /></p>
                  <div className="text-sm">
                    <span style={{ color: 'var(--foreground-tertiary)' }}>你的答案:</span>{' '}
                    <span style={{ color: q.is_correct ? 'var(--success)' : 'var(--error)' }}>{q.user_answer}</span>
                    {!q.is_correct && (
                      <>
                        <span className="mx-2" style={{ color: 'var(--foreground-tertiary)' }}>|</span>
                        <span style={{ color: 'var(--foreground-tertiary)' }}>正确答案:</span>{' '}
                        <span style={{ color: 'var(--success)' }}>{q.correct_answer}</span>
                      </>
                    )}
                  </div>
                  {q.explanation && (
                    <div className="mt-2 p-2 text-sm" style={{ background: 'var(--card-bg)', borderRadius: 'var(--radius-sm)' }}>
                      <span style={{ color: 'var(--foreground-title)' }}>解析:</span>{' '}
                      <span style={{ color: 'var(--foreground)' }}><LaTeXRenderer content={q.explanation} /></span>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="text-center flex gap-4 justify-center">
              <button onClick={() => router.push('/courses')} className="px-6 py-2 text-white" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-md)' }}>返回课程</button>
              {result.wrong > 0 && courseId && (
                <button 
                  onClick={() => router.push(`/mistakes?course_id=${courseId}`)} 
                  className="px-6 py-2" 
                  style={{ background: 'var(--error)', color: 'white', borderRadius: 'var(--radius-md)' }}
                >
                  去错题本
                </button>
              )}
            </div>
          </div>
        ) : currentQuestion ? (
          /* 答题中状态 */
          <div className="p-6" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 text-sm font-semibold text-white" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-full)' }}>
                  {currentIndex + 1} / {questions.length}
                </span>
                <span className="px-2 py-1 text-xs" style={{ background: currentQuestion.question_type === 'single_choice' ? 'var(--info-light)' : currentQuestion.question_type === 'multiple_choice' ? 'var(--warning)' : 'var(--success-light)', color: currentQuestion.question_type === 'single_choice' ? 'var(--info-dark)' : currentQuestion.question_type === 'multiple_choice' ? '#fff' : 'var(--success-dark)', borderRadius: 'var(--radius-sm)' }}>
                  {currentQuestion.question_type === 'single_choice' ? '单选题' : currentQuestion.question_type === 'multiple_choice' ? '多选题' : '判断题'}
                </span>
              </div>
              <span className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>
                {questions.filter(q => q.user_answer !== null).length} 题已答
              </span>
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
                        {isSelected && <span className="ml-2" style={{ color: 'var(--primary)' }}>✓</span>}
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
                      {currentQuestion.user_answer === key && <span className="ml-2" style={{ color: 'var(--primary)' }}>✓</span>}
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
              {currentIndex === questions.length - 1 ? (
                <button
                  onClick={finishBatch}
                  disabled={submitting || !questions.every(q => q.user_answer !== null)}
                  className="flex-1 py-3 font-medium text-white disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, var(--success), #14B8A6)', borderRadius: 'var(--radius-md)' }}
                >
                  {submitting ? '提交中...' : '完成刷题'}
                </button>
              ) : (
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
        ) : null}

        {/* Phase 3 Active Intervention Modal */}
        {/* 关键业务逻辑：连续答错3题后弹出建议 AI 诊断的模态框 */}
        {showInterventionModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.5)' }}>
            <div className="max-w-md w-full mx-4 p-6" style={{ background: 'var(--card-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--card-border)' }}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 flex items-center justify-center" style={{ background: 'var(--warning)', borderRadius: 'var(--radius-full)' }}>
                  <span className="text-2xl">🤖</span>
                </div>
                <div>
                  <h3 className="font-bold" style={{ color: 'var(--foreground-title)' }}>需要一些帮助吗？</h3>
                  <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>检测到您连续答错了 {consecutiveWrongCount} 道题</p>
                </div>
              </div>
              
              <p className="mb-4" style={{ color: 'var(--foreground)' }}>
                AI 可以帮您分析这些错题，找出知识盲区并提供针对性的学习建议。是否现在就去错题本进行 AI 会诊？
              </p>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setShowInterventionModal(false)}
                  className="flex-1 py-2 font-medium"
                  style={{ background: 'var(--background-secondary)', color: 'var(--foreground)', borderRadius: 'var(--radius-md)' }}
                >
                  稍后再说
                </button>
                <button
                  onClick={() => {
                    setShowInterventionModal(false);
                    router.push(`/mistakes?course_id=${courseId}`);
                  }}
                  className="flex-1 py-2 font-medium text-white"
                  style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-md)' }}
                >
                  前往错题本
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function QuizPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--background)' }}><p style={{ color: 'var(--foreground-secondary)' }}>加载中...</p></div>}>
      <QuizPageContent />
    </Suspense>
  );
}
