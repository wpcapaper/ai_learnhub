'use client';

import { useEffect, useState } from 'react';
import { apiClient, Course, User } from '@/lib/api';
import Link from 'next/link';

export default function CoursesPage() {
  const [user, setUser] = useState<User | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [checkingQuiz, setCheckingQuiz] = useState<string | null>(null);

  const fetchCourses = async () => {
    setLoading(true);
    setError('');

    try {
      const data = await apiClient.getCourses(true, user?.id);
      setCourses(data);
    } catch (err) {
      console.error('Failed to fetch courses:', err);
      setError('加载课程列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadUser = async () => {
      const savedUserId = localStorage.getItem('userId');
      if (savedUserId) {
        const userData = await apiClient.getUser(savedUserId);
        setUser(userData);
      }
    };

    loadUser();
  }, []);

  useEffect(() => {
    if (user) {
      fetchCourses();
    }
  }, [user]);

  const handleLogout = () => {
    localStorage.removeItem('userId');
    setUser(null);
  };

  const handleStartQuiz = async (course: Course) => {
    if (!user) {
      alert('请先登录');
      return;
    }

    setCheckingQuiz(course.id);

    try {
      const nextQuestions = await apiClient.getNextQuestions(user.id, course.id, 1, false);

      if (nextQuestions.length === 0 && (course.total_questions || 0) > 0) {
        const shouldStartNewRound = confirm('当前轮次已刷完，是否开启新的轮次？');
        if (shouldStartNewRound) {
          window.location.href = `/quiz?course_id=${course.id}`;
        } else {
          setCheckingQuiz(null);
        }
      } else {
        window.location.href = `/quiz?course_id=${course.id}`;
      }
    } catch (error) {
      console.error('Failed to check quiz availability:', error);
      alert('检查刷题状态失败');
      setCheckingQuiz(null);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--background)' }}>
        <div 
          className="w-full max-w-md p-8 text-center"
          style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--card-border)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <div 
            className="w-14 h-14 mx-auto mb-4 flex items-center justify-center"
            style={{ 
              background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground-title)' }}>
            AILearn Hub
          </h1>
          <p className="mb-6" style={{ color: 'var(--foreground-secondary)' }}>
            请先登录以查看课程
          </p>
          <Link 
            href="/"
            className="inline-block py-3 px-6 text-white font-medium"
            style={{
              background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            返回首页
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--background)' }}>
      <nav 
        className="sticky top-0 z-50 border-b"
        style={{ 
          background: 'var(--card-bg)',
          borderColor: 'var(--card-border)',
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-14">
            <div className="flex items-center gap-3">
              <Link href="/" className="flex items-center gap-2">
                <div 
                  className="w-9 h-9 flex items-center justify-center"
                  style={{ 
                    background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <span className="text-lg font-bold" style={{ color: 'var(--foreground-title)' }}>
                  AILearn Hub
                </span>
              </Link>
              <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
              <span style={{ color: 'var(--foreground-title)' }}>选择课程</span>
            </div>
            <div className="flex items-center gap-3">
              <span 
                className="hidden sm:block px-3 py-1 text-sm"
                style={{ 
                  background: 'var(--primary-bg)',
                  color: 'var(--primary)',
                  borderRadius: 'var(--radius-full)',
                }}
              >
                {user?.nickname || user?.username}
              </span>
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 text-sm"
                style={{ 
                  color: 'var(--error)',
                  background: 'var(--error-light)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                退出
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground-title)' }}>
            选择课程
          </h1>
          <p style={{ color: 'var(--foreground-secondary)' }}>
            请选择一个课程开始学习
          </p>
        </div>

        {error && (
          <div 
            className="mb-6 p-4"
            style={{ 
              background: 'var(--error-light)',
              color: 'var(--error-dark)',
              border: '1px solid var(--error)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div 
              className="inline-block h-8 w-8 border-2 rounded-full animate-spin"
              style={{ 
                borderColor: 'var(--card-border)',
                borderTopColor: 'var(--primary)',
              }}
            />
            <p className="mt-4" style={{ color: 'var(--foreground-secondary)' }}>加载中...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map((course) => (
              <div
                key={course.id}
                className="flex flex-col"
                style={{
                  background: 'var(--card-bg)',
                  border: '1px solid var(--card-border)',
                  borderRadius: 'var(--radius-lg)',
                }}
              >
                <div className="p-5 flex flex-col flex-grow">
                  <div className="flex items-center gap-3 mb-3">
                    <span 
                      className="text-xs px-2 py-1 flex-shrink-0"
                      style={{ 
                        background: 'var(--primary-bg)',
                        color: 'var(--primary)',
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      {course.course_type === 'exam' ? '考试类' : '学习类'}
                    </span>
                    <h2 className="text-lg font-bold truncate" style={{ color: 'var(--foreground-title)' }} title={course.title}>
                      {course.title}
                    </h2>
                  </div>
                  
                  {course.description && (
                    <p className="mb-4 text-sm line-clamp-2" style={{ color: 'var(--foreground-secondary)' }}>
                      {course.description}
                    </p>
                  )}

                  {(course.total_questions || 0) > 0 && (
                    <div className="mt-auto mb-4">
                      <div className="flex justify-between text-sm mb-2" style={{ color: 'var(--foreground-secondary)' }}>
                        <span>题目: <strong style={{ color: 'var(--foreground-title)' }}>{course.total_questions}</strong></span>
                        <span>已刷: <strong style={{ color: 'var(--primary)' }}>{course.answered_questions || 0}</strong></span>
                      </div>
                      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--background-secondary)' }}>
                        <div 
                          className="h-full rounded-full"
                          style={{
                            width: `${((course.answered_questions || 0) / (course.total_questions || 1)) * 100}%`,
                            background: 'linear-gradient(90deg, var(--primary), var(--primary-light))',
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div className="p-4 border-t" style={{ borderColor: 'var(--card-border)' }}>
                  <div className={`grid gap-2 ${(course.total_questions || 0) > 0 || course.course_type === 'exam' ? 'grid-cols-3' : 'grid-cols-1'}`}>
                    {course.course_type === 'exam' ? (
                      <>
                        <button
                          onClick={() => handleStartQuiz(course)}
                          disabled={checkingQuiz === course.id}
                          className="py-2 text-sm font-medium disabled:opacity-50"
                          style={{ 
                            background: 'var(--primary-bg)',
                            color: 'var(--primary)',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          {checkingQuiz === course.id ? '...' : '刷题'}
                        </button>
                        <Link
                          href={`/exam?course_id=${course.id}`}
                          className="py-2 text-sm font-medium text-center"
                          style={{ 
                            background: 'var(--info-light)',
                            color: 'var(--info-dark)',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          考试
                        </Link>
                        <Link
                          href={`/mistakes?course_id=${course.id}`}
                          className="py-2 text-sm font-medium text-center"
                          style={{ 
                            background: 'var(--error-light)',
                            color: 'var(--error-dark)',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          错题
                        </Link>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => (window.location.href = `/chapters?course_id=${course.id}`)}
                          className="py-2 text-sm font-medium"
                          style={{ 
                            background: 'var(--success-light)',
                            color: 'var(--success-dark)',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          学习
                        </button>
                        {(course.total_questions || 0) > 0 && (
                          <>
                            <button
                              onClick={() => handleStartQuiz(course)}
                              disabled={checkingQuiz === course.id}
                              className="py-2 text-sm font-medium disabled:opacity-50"
                              style={{ 
                                background: 'var(--primary-bg)',
                                color: 'var(--primary)',
                                borderRadius: 'var(--radius-sm)',
                              }}
                            >
                              {checkingQuiz === course.id ? '...' : '刷题'}
                            </button>
                            <Link
                              href={`/mistakes?course_id=${course.id}`}
                              className="py-2 text-sm font-medium text-center"
                              style={{ 
                                background: 'var(--error-light)',
                                color: 'var(--error-dark)',
                                borderRadius: 'var(--radius-sm)',
                              }}
                            >
                              错题
                            </Link>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && courses.length === 0 && (
          <div 
            className="text-center py-12"
            style={{
              background: 'var(--card-bg)',
              border: '1px solid var(--card-border)',
              borderRadius: 'var(--radius-lg)',
            }}
          >
            <p style={{ color: 'var(--foreground-secondary)' }}>暂无可用课程</p>
          </div>
        )}
      </div>
    </div>
  );
}
