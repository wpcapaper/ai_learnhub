'use client';

import { useEffect, useState } from 'react';
import { apiClient, Course, QuestionSet, User } from '@/lib/api';
import Link from 'next/link';

export default function CoursesPage() {
  const [user, setUser] = useState<User | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // 关键业务逻辑：状态用于控制刷题模式点击时的检查流程
  // checkingQuiz: 正在检查是否可以开始刷题（用于显示加载状态）
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

  /**
   * 处理刷题模式点击
   *
   * 关键业务逻辑：
   * - 默认使用 allow_new_round=false 检查是否有未刷过的题
   * - 如果返回题目数=0 且课程题目总数>0，弹窗询问是否开启新轮
   * - 如果用户确认，则使用 allow_new_round=true 跳转到刷题页面
   */
  const handleStartQuiz = async (course: Course) => {
    if (!user) {
      alert('请先登录');
      return;
    }

    setCheckingQuiz(course.id);

    try {
      // 关键业务逻辑：默认 allow_new_round=false，只检查当前轮次未刷过的题
      const nextQuestions = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/review/next?user_id=${user.id}&course_type=${course.course_type}&batch_size=1&allow_new_round=false`
      ).then(res => res.json());

      // 关键业务逻辑：如果没有未刷过的题，且课程有题目，询问是否开启新轮
      if (nextQuestions.length === 0 && (course.total_questions || 0) > 0) {
        const shouldStartNewRound = confirm('当前轮次已刷完，是否开启新的轮次？');
        if (shouldStartNewRound) {
          // 用户确认开启新轮，跳转到刷题页面（后端会自动开启新轮）
          window.location.href = `/quiz?course_id=${course.id}`;
        } else {
          // 用户取消，不做任何操作
          setCheckingQuiz(null);
        }
      } else {
        // 仍有未刷过的题，直接跳转到刷题页面
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
              <Link href="/courses" className="ml-4 text-2xl font-bold text-gray-800 hover:text-gray-900">
                选择课程
              </Link>
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
            选择课程
          </h1>
          <p className="text-gray-700">
            请选择一个课程开始学习
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-100 text-red-700 p-4 rounded-md">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 border-4 border-t-gray-300 rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-700">加载中...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map((course) => (
              <div
                key={course.id}
                className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow overflow-hidden"
              >
                <div className="p-6">
                  <h2 className="text-xl font-bold text-gray-800 mb-2">
                    {course.title}
                  </h2>
                  {course.description && (
                    <p className="text-gray-700 mb-4 text-sm">
                      {course.description}
                    </p>
                  )}
                  <div className="text-xs text-gray-500 mb-4">
                    <span className="inline-block mr-3">
                      {course.course_type === 'exam' ? '考试类' : '学习类'}
                    </span>
                    {course.is_active ? (
                      <span className="inline-block px-2 py-1 bg-green-100 text-green-700 rounded-full">
                        可用
                      </span>
                    ) : (
                      <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 rounded-full">
                        不可用
                      </span>
                    )}
                  </div>
                  {course.course_type === 'exam' && (
                    <div className="text-sm text-gray-600 mb-4">
                      <div className="flex justify-between mb-2">
                        <span>题目总数: <strong>{course.total_questions || 0}</strong></span>
                        <span>已刷题目: <strong>{course.answered_questions || 0}</strong></span>
                      </div>
                      {/* 显示当前轮次信息 */}
                      <div className="text-center bg-blue-50 rounded-md py-2 px-4">
                        <span className="text-blue-700 font-medium">
                          第 {course.current_round || 1} 轮
                          {(course.total_rounds_completed || 0) > 0 && ` (已完成 ${course.total_rounds_completed} 轮)`}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="border-t border-gray-200">
                  <div className="grid grid-cols-3 gap-2 p-4">
                    {/* 关键业务逻辑：刷题模式按钮改为可点击的按钮，增加检查逻辑 */}
                    <button
                      onClick={() => handleStartQuiz(course)}
                      disabled={checkingQuiz === course.id}
                      className="bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium rounded-md py-3 px-4 text-center transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {checkingQuiz === course.id ? '检查中...' : '刷题模式'}
                    </button>
                    <Link
                      href={`/exam?course_id=${course.id}`}
                      className="block bg-purple-50 hover:bg-purple-100 text-purple-700 font-medium rounded-md py-3 px-4 text-center transition-colors text-sm"
                    >
                      考试模式
                    </Link>
                    <Link
                      href={`/mistakes?course_id=${course.id}`}
                      className="block bg-red-50 hover:bg-red-100 text-red-700 font-medium rounded-md py-3 px-4 text-center transition-colors text-sm"
                    >
                      错题本
                    </Link>
                  </div>
                </div>

                {course.default_exam_config && (
                  <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
                    <div className="text-sm">
                      <p className="font-semibold text-gray-800 mb-1">
                        默认考试配置：
                      </p>
                      <div className="space-y-1 text-gray-700">
                        <p>
                          <span className="font-medium">单选题：</span>
                          {course.default_exam_config.question_type_config?.single_choice || 30}题
                        </p>
                        <p>
                          <span className="font-medium">多选题：</span>
                          {course.default_exam_config.question_type_config?.multiple_choice || 10}题
                        </p>
                        <p>
                          <span className="font-medium">判断题：</span>
                          {course.default_exam_config.question_type_config?.true_false || 10}题
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {!loading && courses.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow-md">
            <p className="text-gray-700">
              暂无可用课程
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
