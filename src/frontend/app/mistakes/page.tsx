'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient, Question, Course, User } from '@/lib/api';
import LaTeXRenderer from '@/components/LaTeXRenderer';
import Link from 'next/link';
import ThemeSelector from '@/components/ThemeSelector';

function MistakesPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const courseId = searchParams.get('course_id');

  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [mistakes, setMistakes] = useState<Question[]>([]);
  const [stats, setStats] = useState<{ total_wrong: number; wrong_by_type: Record<string, number> } | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      apiClient.getUser(savedUserId).then(setUser);
    } else {
      router.push('/');
    }
  }, [router]);

  useEffect(() => {
    if (!user || !courseId) return;

    const loadData = async () => {
      try {
        const [courseData, mistakesData, statsData] = await Promise.all([
          apiClient.getCourse(courseId!),
          apiClient.getMistakes(user.id, courseId!),
          apiClient.getMistakesStats(user.id, courseId!),
        ]);
        setCourse(courseData);
        setMistakes(mistakesData);
        setStats(statsData);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load mistakes:', err);
        setLoading(false);
      }
    };

    loadData();
  }, [user, courseId]);

  const handleRetryMistakes = async () => {
    if (!user || !courseId) return;

    setRetrying(true);
    try {
      const result = await apiClient.retryMistakes(user.id, courseId, 10);
      if (result.questions.length > 0) {
        router.push(`/quiz?course_id=${courseId}`);
      } else {
        alert('没有需要重练的错题');
      }
    } catch (error) {
      console.error('Failed to retry mistakes:', error);
      alert('重练错题失败');
    } finally {
      setRetrying(false);
    }
  };

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
              <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
              <Link href="/courses" style={{ color: 'var(--foreground-title)' }}>选择课程</Link>
              {course && (
                <>
                  <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
                  <span style={{ color: 'var(--foreground-secondary)' }}>{course.title}</span>
                </>
              )}
              <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
              <span style={{ color: 'var(--error)' }}>错题本</span>
            </div>
            <div className="flex items-center gap-3">
              <ThemeSelector />
              <button onClick={() => router.push('/courses')} className="px-3 py-1.5 text-sm" style={{ background: 'var(--background-secondary)', color: 'var(--foreground-secondary)', borderRadius: 'var(--radius-sm)' }}>返回课程</button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground-title)' }}>错题本</h1>
            <p style={{ color: 'var(--foreground-secondary)' }}>查看和管理你的错题</p>
          </div>
          {mistakes.length > 0 && (
            <button
              onClick={handleRetryMistakes}
              disabled={retrying}
              className="px-6 py-2 text-white font-medium disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-md)' }}
            >
              {retrying ? '加载中...' : '重练错题'}
            </button>
          )}
        </div>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="p-4" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
              <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>总错题数</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--error)' }}>{stats.total_wrong}</p>
            </div>
            <div className="p-4" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
              <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>单选题</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--foreground-title)' }}>{stats.wrong_by_type?.single_choice || 0}</p>
            </div>
            <div className="p-4" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
              <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>多选题</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--foreground-title)' }}>{stats.wrong_by_type?.multiple_choice || 0}</p>
            </div>
            <div className="p-4" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
              <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>判断题</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--foreground-title)' }}>{stats.wrong_by_type?.true_false || 0}</p>
            </div>
          </div>
        )}

        {mistakes.length > 0 ? (
          <div className="space-y-4">
            {mistakes.map((question, index) => (
              <div
                key={question.id}
                className="p-6"
                style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className="px-2 py-1 text-xs" style={{ background: question.question_type === 'single_choice' ? 'var(--info-light)' : question.question_type === 'multiple_choice' ? 'var(--warning)' : 'var(--success-light)', color: question.question_type === 'single_choice' ? 'var(--info-dark)' : question.question_type === 'multiple_choice' ? '#fff' : 'var(--success-dark)', borderRadius: 'var(--radius-sm)' }}>
                    {question.question_type === 'single_choice' ? '单选题' : question.question_type === 'multiple_choice' ? '多选题' : '判断题'}
                  </span>
                  {question.last_wrong_time && (
                    <span className="text-xs" style={{ color: 'var(--foreground-tertiary)' }}>
                      错误时间: {new Date(question.last_wrong_time).toLocaleDateString()}
                    </span>
                  )}
                </div>

                <p className="font-medium mb-4" style={{ color: 'var(--foreground-title)' }}>
                  {index + 1}. <LaTeXRenderer content={question.content} />
                </p>

                {question.options && (
                  <div className="space-y-2 mb-4">
                    {Object.entries(question.options).map(([key, value]) => {
                      const isCorrect = question.correct_answer?.includes(key);
                      const isUserAnswer = question.user_answer?.includes(key);
                      return (
                        <div
                          key={key}
                          className="p-3"
                          style={{
                            background: isCorrect ? 'var(--success-light)' : isUserAnswer ? 'var(--error-light)' : 'var(--background-secondary)',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          <strong style={{ color: isCorrect ? 'var(--success-dark)' : isUserAnswer ? 'var(--error-dark)' : 'var(--foreground-title)' }}>{key}.</strong>{' '}
                          <span style={{ color: 'var(--foreground-title)' }}><LaTeXRenderer content={value} /></span>
                          {isCorrect && <span className="ml-2" style={{ color: 'var(--success)' }}>✓ 正确</span>}
                          {isUserAnswer && !isCorrect && <span className="ml-2" style={{ color: 'var(--error)' }}>✗ 你的答案</span>}
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="flex gap-4 text-sm">
                  <div>
                    <span style={{ color: 'var(--foreground-tertiary)' }}>你的答案:</span>{' '}
                    <span style={{ color: 'var(--error)' }}>{question.user_answer || '未作答'}</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--foreground-tertiary)' }}>正确答案:</span>{' '}
                    <span style={{ color: 'var(--success)' }}>{question.correct_answer}</span>
                  </div>
                </div>

                {question.explanation && (
                  <div className="mt-4 p-3" style={{ background: 'var(--background-secondary)', borderRadius: 'var(--radius-sm)' }}>
                    <span className="font-medium" style={{ color: 'var(--foreground-title)' }}>解析:</span>
                    <p className="mt-1" style={{ color: 'var(--foreground)' }}><LaTeXRenderer content={question.explanation} /></p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
            <div className="w-16 h-16 mx-auto mb-4 flex items-center justify-center" style={{ background: 'var(--success-light)', borderRadius: 'var(--radius-full)' }}>
              <svg className="w-8 h-8" style={{ color: 'var(--success)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-lg font-medium mb-2" style={{ color: 'var(--foreground-title)' }}>太棒了！</p>
            <p style={{ color: 'var(--foreground-secondary)' }}>暂无错题，继续保持！</p>
          </div>
        )}

        <button onClick={() => router.push('/courses')} className="mt-8 flex items-center gap-1 text-sm" style={{ color: 'var(--primary)' }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          返回课程列表
        </button>
      </div>
    </div>
  );
}

export default function MistakesPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--background)' }}><p style={{ color: 'var(--foreground-secondary)' }}>加载中...</p></div>}>
      <MistakesPageContent />
    </Suspense>
  );
}
