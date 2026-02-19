'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import type { Course, User } from '@/lib/api';
import MarkdownReader from '@/components/MarkdownReader';
import AIAssistant from '@/components/AIAssistant';

function LearningPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const courseId = searchParams.get('course_id');
  const initialChapterId = searchParams.get('chapter_id');

  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [currentChapter, setCurrentChapter] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const handleLogout = () => {
    localStorage.removeItem('userId');
    setUser(null);
    window.location.reload();
  };

  // 从 localStorage 加载用户
  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      apiClient.getUser(savedUserId).then(setUser);
    }
  }, []);

  // 加载课程和章节内容
  useEffect(() => {
    if (!user || !courseId) return;

    const loadData = async () => {
      try {
        // 并行加载课程和章节列表
        const [courseData, chaptersData] = await Promise.all([
          apiClient.getCourse(courseId!),
          apiClient.getLearningChapters(courseId!),
        ]);

        setCourse(courseData);

        // 确定要加载的章节ID
        const targetChapterId = initialChapterId || chaptersData[0]?.id;

        if (targetChapterId) {
          // 加载选定章节的完整内容（包括markdown）
          const chapterContent = await apiClient.getChapterContent(targetChapterId, user.id);
          setCurrentChapter(chapterContent);
        }

        setLoading(false);
      } catch (err) {
        setError(`加载数据失败: ${(err as Error).message}`);
        setLoading(false);
      }
    };

    loadData();
  }, [user, courseId, initialChapterId]);

  // 处理阅读进度更新
  const handleProgressChange = useCallback(async (position: number, percentage: number) => {
    if (!user || !currentChapter) return;

    try {
      await apiClient.updateReadingProgress(
        currentChapter.id,
        user.id,
        { last_position: position, last_percentage: percentage }
      );
    } catch (err) {
      console.error('更新进度失败:', err);
    }
  }, [user, currentChapter]);

  // 处理章节完成
  const handleChapterComplete = useCallback(async () => {
    if (!user || !currentChapter) return;

    try {
      await apiClient.markChapterCompleted(currentChapter.id, user.id);
      // 标记为已完成
      setCurrentChapter((prev: any) => ({
        ...prev,
        user_progress: {
          ...prev.user_progress,
          is_completed: true,
        }
      }));
    } catch (err) {
      console.error('标记章节完成失败:', err);
    }
  }, [user, currentChapter]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-4 border-t-slate-200 rounded-full animate-spin"></div>
          <p className="mt-4 text-slate-700">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="bg-red-50 text-red-700 px-6 py-4 rounded-lg max-w-md">
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
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-slate-700">课程不存在</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <button
                onClick={() => router.push('/courses')}
                className="text-2xl font-bold text-slate-800 hover:text-slate-900"
              >
                AILearn Hub
              </button>
              <span className="ml-4 text-slate-400">/</span>
              <button
                onClick={() => router.push(`/chapters?course_id=${courseId}`)}
                className="ml-4 text-xl font-bold text-slate-800 hover:text-slate-900"
              >
                {course.title}
              </button>
            </div>
            <div className="flex items-center space-x-4">
              {user && (
                <>
                  <span className="text-sm text-slate-700">
                    {user.nickname || user.username}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="text-slate-700 hover:text-slate-900 px-3 py-2 rounded-md text-sm font-medium hover:bg-slate-100 transition-colors"
                  >
                    切换用户
                  </button>
                </>
              )}
              <button
                onClick={() => router.push('/courses')}
                className="text-slate-700 hover:text-slate-900 px-3 py-2 rounded-md text-sm font-medium hover:bg-slate-100 transition-colors"
              >
                返回课程
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 主内容区域 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 返回章节列表按钮 */}
        <div className="mb-4">
          <button
            onClick={() => router.push(`/chapters?course_id=${courseId}`)}
            className="text-slate-600 hover:text-slate-900 font-medium hover:underline"
          >
            ← 返回章节列表
          </button>
        </div>

        <div className="flex gap-6 h-[calc(100vh-12rem)]">
          {/* 左侧：Markdown 阅读器（占据更大空间，可以滚动） */}
          <div className="flex-[2] flex flex-col min-w-0 overflow-hidden">
            {/* 当前章节标题 */}
            <div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
              <h1 className="text-xl font-bold text-slate-900 mb-2">
                {currentChapter?.title}
              </h1>
              {/* 阅读进度指示 */}
              {currentChapter?.user_progress && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">
                    阅读进度: {currentChapter.user_progress.last_percentage.toFixed(1)}%
                  </span>
                  {!currentChapter.user_progress.is_completed && (
                    <button
                      onClick={handleChapterComplete}
                      className="px-3 py-1.5 text-sm bg-emerald-600 text-white rounded-md hover:bg-emerald-700 transition-colors"
                    >
                      标记为已完成
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Markdown 内容 */}
            {currentChapter && (
              <div className="flex-1 overflow-y-auto bg-white">
                <MarkdownReader
                  content={currentChapter.content_markdown}
                  onProgressChange={handleProgressChange}
                  courseDirName={currentChapter.course_dir_name}
                  chapterPath={currentChapter.file_path}
                />
              </div>
            )}
          </div>

          {/* 右侧：AI 助手（固定在视口内） */}
          <div className="flex-1 flex-shrink-0 w-96 bg-white border-l border-slate-200 overflow-hidden">
            {user ? (
              <AIAssistant
                chapterId={currentChapter?.id || ''}
                userId={user.id}
              />
            ) : (
              <div className="h-full flex items-center justify-center p-8">
                <p className="text-slate-500 text-center text-sm">
                  请先登录以使用 AI 助手
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LearningPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="inline-block h-8 w-8 border-4 border-t-gray-200 rounded-full animate-spin"></div>
        <p className="ml-4 text-gray-700">加载中...</p>
      </div>
    }>
      <LearningPageContent />
    </Suspense>
  );
}
