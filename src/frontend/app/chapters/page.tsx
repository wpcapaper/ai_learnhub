'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient, Course, User } from '@/lib/api';
import Link from 'next/link';

function ChaptersPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const courseId = searchParams.get('course_id');

  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 从 localStorage 加载用户
  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      apiClient.getUser(savedUserId).then(setUser);
    }
  }, []);

  // 加载课程和章节数据
  useEffect(() => {
    if (!courseId) {
      setError('缺少课程 ID');
      setLoading(false);
      return;
    }

    Promise.all([
      apiClient.getCourse(courseId),
      apiClient.getLearningChapters(courseId),
    ]).then(([courseData, chaptersData]) => {
      setCourse(courseData);
      setChapters(chaptersData);
      setLoading(false);
    }).catch((err) => {
      setError(`加载数据失败: ${err.message}`);
      setLoading(false);
    });
  }, [courseId]);

  // 处理章节选择
  const handleChapterSelect = (chapterId: string) => {
    router.push(`/learning?course_id=${courseId}&chapter_id=${chapterId}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-4 border-t-gray-200 rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-700">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-red-100 text-red-700 px-6 py-4 rounded-lg max-w-md">
          <p className="font-semibold">加载失败</p>
          <p className="mt-2">{error}</p>
          <button
            onClick={() => router.push('/courses')}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            返回课程列表
          </button>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-700">课程不存在</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* 顶部导航栏 */}
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
              <span className="ml-4 text-gray-400">/</span>
              <span className="ml-4 text-2xl font-bold text-gray-800">
                {course.title}
              </span>
            </div>
            <div className="flex items-center space-x-4">
              {user && (
                <button
                  onClick={() => {
                    localStorage.removeItem('userId');
                    setUser(null);
                    window.location.reload();
                  }}
                  className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                >
                  {user.nickname || user.username}
                </button>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* 主内容区域 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            选择章节
          </h1>
          <p className="text-gray-700">
            请选择要学习的章节
          </p>
        </div>

        {/* 章节列表 */}
        {chapters.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer p-6 border-2 border-transparent hover:border-green-500"
                onClick={() => handleChapterSelect(chapter.id)}
              >
                <div className="flex items-start mb-3">
                  <span className="flex-shrink-0 w-10 h-10 bg-green-100 text-green-700 rounded-full flex items-center justify-center font-bold text-lg">
                    {chapter.sort_order}
                  </span>
                  <div className="ml-3 flex-1">
                    <h2 className="text-xl font-bold text-gray-800 mb-2">
                      {chapter.title}
                    </h2>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-4">
                  <span className="text-sm text-gray-500">
                    {chapter.user_progress ? (
                      <span className="text-green-600">
                        ✓ 已完成 {chapter.user_progress.last_percentage.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-gray-400">未开始</span>
                    )}
                  </span>
                  <span className="text-sm text-green-600 font-medium">
                    开始学习 →
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <p className="text-gray-700 mb-4">
              暂无可用章节
            </p>
            <button
              onClick={() => router.push('/courses')}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              返回课程列表
            </button>
          </div>
        )}

        {/* 返回按钮 */}
        <div className="mt-8">
          <button
            onClick={() => router.push('/courses')}
            className="text-gray-600 hover:text-gray-900 font-medium"
          >
            ← 返回课程列表
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ChaptersPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-4 border-t-gray-200 rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-700">加载中...</p>
        </div>
      </div>
    }>
      <ChaptersPageContent />
    </Suspense>
  );
}
