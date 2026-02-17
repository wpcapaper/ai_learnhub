'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiClient, Question, User, Course } from '@/lib/api';
import Link from 'next/link';
import LaTeXRenderer from '@/components/LaTeXRenderer';

interface MistakesStats {
  total_wrong: number;
  wrong_by_course: Record<string, number>;
  wrong_by_type: Record<string, number>;
}

function MistakesPageContent() {
  const searchParams = useSearchParams();
  const courseId = searchParams.get('course_id') || undefined;
  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [mistakes, setMistakes] = useState<Question[]>([]);
  const [stats, setStats] = useState<MistakesStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');

    try {
      if (!user) return;

      // Fetch mistakes and stats
      const [mistakesData, statsData] = await Promise.all([
        apiClient.getMistakes(user.id, courseId),
        apiClient.getMistakesStats(user.id, courseId),
      ]);

      setMistakes(mistakesData);
      setStats(statsData);
    } catch (err) {
      console.error('Failed to fetch mistakes:', err);
      setError('加载错题数据失败');
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
        fetchData();
      }

      if (courseId) {
        const courseData = await apiClient.getCourse(courseId);
        setCourse(courseData);
      }
    };

    loadUser();
  }, [courseId]);

  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user]);

  const handleLogout = () => {
    localStorage.removeItem('userId');
    setUser(null);
  };

  const handleRetryAll = async () => {
    if (!user) return;

    try {
      // 调用全部错题重练API，创建包含所有错题的批次
      const result = await apiClient.retryAllMistakes(user.id, courseId || undefined);

      // 跳转到刷题页面，传递batch_id参数
      // 关键业务逻辑：通过batch_id让刷题页面加载所有错题
      const url = `/quiz?batch_id=${result.batch_id}`;
      window.location.href = url;
    } catch (error) {
      console.error('Failed to start wrong answer practice:', error);
      alert('开始错题重练失败: ' + (error as Error).message);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full mx-auto p-6">
          <div className="bg-white rounded-lg shadow-md p-8">
            <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">
              AILearn Hub
            </h1>
            <p className="text-center text-gray-700 mb-8">
              请先登录
            </p>

            <a
              href="/"
              className="block w-full bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md py-2.5 px-4 text-center transition-colors"
            >
              返回首页
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-gray-800 hover:text-gray-900">
                AILearn Hub
              </Link>
              <span className="ml-4 text-gray-400">/</span>
              {course && (
                <>
                  <Link href="/courses" className="ml-4 text-2xl font-bold text-gray-800 hover:text-gray-900">
                    {course.title}
                  </Link>
                  <span className="ml-4 text-gray-400">/</span>
                  <span className="ml-4 text-2xl font-bold text-gray-800">
                    错题本
                  </span>
                </>
              )}
              {!course && (
                <span className="ml-4 text-2xl font-bold text-gray-800">
                  错题本
                </span>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                {user?.nickname || user?.username}
              </span>
              <button
                onClick={handleLogout}
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                切换用户
              </button>
              <Link
                href="/stats"
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                统计
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            错题本
          </h1>
          <p className="text-gray-700">
            查看您的错题并重点复习
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-100 text-red-700 p-4 rounded-md">
            {error}
          </div>
        )}

        {/* Stats Card */}
        {stats && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-700 mb-1">总错题数</div>
                <div className="text-3xl font-bold text-red-600">{stats.total_wrong}</div>
              </div>
              <div>
                <div className="text-sm text-gray-700 mb-1">按题型</div>
                <div className="text-sm">
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-700">单选题</span>
                    <span className="font-medium text-gray-900">{stats.wrong_by_type.single_choice || 0}题</span>
                  </div>
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-700">多选题</span>
                    <span className="font-medium text-gray-900">{stats.wrong_by_type.multiple_choice || 0}题</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-700">判断题</span>
                    <span className="font-medium text-gray-900">{stats.wrong_by_type.true_false || 0}题</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 错题重练按钮 */}
        {stats && stats.total_wrong > 0 && (
          <div className="mb-6">
            <button
              onClick={handleRetryAll}
              className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-4 px-6 rounded-lg shadow-md transition-all hover:shadow-lg"
            >
              开始错题重练 ({stats.total_wrong} 题)
            </button>
            <p className="text-sm text-gray-600 mt-2 text-center">
              系统会自动创建包含所有错题的刷题批次
            </p>
          </div>
        )}

        {/* Mistakes List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 border-4 border-t-gray-300 rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-700">加载中...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {mistakes.map((mistake, index) => (
              <div
                key={mistake.id || index}
                className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow overflow-hidden"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-700">
                          第{index + 1}题
                        </span>
                        {/* 错题本中调整tag颜色以区分题型，多选题使用醒目颜色 */}
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          mistake.question_type === 'single_choice' ? 'bg-blue-100 text-blue-700' :
                          mistake.question_type === 'multiple_choice' ? 'bg-orange-500 text-white font-bold' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {mistake.question_type === 'single_choice' ? '单选题' :
                           mistake.question_type === 'multiple_choice' ? '多选题' : '判断题'}
                        </span>
                        {/* 错题本中显示题集来源（显示固定题库名称，而非课程名） */}
                        {mistake.question_set_codes && mistake.question_set_codes.length > 0 && (
                          <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-700">
                            📚 {mistake.question_set_codes.join(', ')}
                          </span>
                        )}
                        {mistake.difficulty && (
                          <span className="px-2 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-700">
                            难度{mistake.difficulty}
                          </span>
                        )}
                        {mistake.last_wrong_time && (
                          <span className="px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-700">
                            最近做错: {new Date(mistake.last_wrong_time!).toLocaleString('zh-CN', {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        )}
                      </div>
                      <p className="text-gray-800 font-medium"><LaTeXRenderer content={mistake.content} /></p>
                    </div>
                  </div>

                  {mistake.options && (
                    <div className="space-y-2 mt-4">
                      {(Array.isArray(mistake.options) ? 
                        mistake.options.map((value: string, index: number) => [String.fromCharCode(65 + index), value] as [string, string]) : 
                        Object.entries(mistake.options).map(([key, value]) => {
                          if (/^\d+$/.test(key)) return [String.fromCharCode(65 + parseInt(key)), value as string] as [string, string];
                          return [key, value as string] as [string, string];
                        })
                      ).map(([key, value]) => {
                        const isCorrect = mistake.correct_answer != null && (
                          // 1. Exact Key Match (Priority 1)
                          mistake.correct_answer.trim().toUpperCase() === key ||
                          // 2. Comma separated keys for multiple choice (e.g. "A,B")
                          (mistake.correct_answer.includes(',') && mistake.correct_answer.split(/[,，\s]+/).map(k => k.trim().toUpperCase()).includes(key)) ||
                          // 3. Exact Value Match (Legacy data)
                          mistake.correct_answer === value
                        );
                        
                        return (
                        <div
                          key={key}
                          className={`flex items-center gap-3 p-2 rounded ${
                            isCorrect
                              ? 'bg-green-50 border border-green-200'
                              : 'bg-gray-50'
                          }`}
                        >
                          <span className="w-10 text-right font-medium text-gray-800">{key}.</span>
                          <strong className="flex-1 text-gray-900"><LaTeXRenderer content={value} /></strong>
                          {isCorrect && (
                            <span className="text-green-600 font-medium text-sm">正确答案</span>
                          )}
                        </div>
                      )})}
                    </div>
                  )}

                  {mistake.explanation && (
                    <div className="mt-4 p-3 bg-blue-50 rounded-md">
                      <div className="text-sm font-medium text-blue-900 mb-1">解析：</div>
                      <p className="text-sm text-blue-800"><LaTeXRenderer content={mistake.explanation} /></p>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {!loading && mistakes.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow-md">
            <p className="text-gray-700">暂无错题</p>
          </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MistakesPage() {
  return (
    <Suspense fallback={<div>加载中...</div>}>
      <MistakesPageContent />
    </Suspense>
  );
}
