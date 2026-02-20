'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import type { Course, User } from '@/lib/api';
import MarkdownReader from '@/components/MarkdownReader';
import AIAssistant from '@/components/AIAssistant';
import ThemeSelector from '@/components/ThemeSelector';

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

  // 禁止页面整体滚动
  useEffect(() => {
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    return () => {
      document.documentElement.style.overflow = '';
      document.body.style.overflow = '';
    };
  }, []);

  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      apiClient.getUser(savedUserId).then(setUser);
    }
  }, []);

  useEffect(() => {
    if (!user || !courseId) return;

    const loadData = async () => {
      try {
        const [courseData, chaptersData] = await Promise.all([
          apiClient.getCourse(courseId!),
          apiClient.getLearningChapters(courseId!),
        ]);

        setCourse(courseData);

        const targetChapterId = initialChapterId || chaptersData[0]?.id;

        if (targetChapterId) {
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

  const handleChapterComplete = useCallback(async () => {
    if (!user || !currentChapter) return;

    try {
      await apiClient.markChapterCompleted(currentChapter.id, user.id);
      setCurrentChapter((prev: any) => ({
        ...prev,
        user_progress: { ...prev.user_progress, is_completed: true },
      }));
    } catch (err) {
      console.error('标记章节完成失败:', err);
    }
  }, [user, currentChapter]);

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

  if (error || !course) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--background)' }}>
        <div className="text-center max-w-md p-8" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
          <p className="mb-4" style={{ color: 'var(--error)' }}>{error || '课程不存在'}</p>
          <button onClick={() => router.push('/courses')} className="px-6 py-2 text-white" style={{ background: 'var(--primary)', borderRadius: 'var(--radius-md)' }}>
            返回课程列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: 'var(--background)' }}>
      <nav className="flex-shrink-0 border-b" style={{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }}>
        <div className="px-3 sm:px-4">
          <div className="flex justify-between h-14">
            <div className="flex items-center gap-2">
              <button onClick={() => router.push('/courses')} className="w-8 h-8 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-sm)' }}>
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </button>
              <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
              <button onClick={() => router.push(`/chapters?course_id=${courseId}`)} style={{ color: 'var(--foreground-title)' }}>{course.title}</button>
            </div>
            <div className="flex items-center gap-2">
              <ThemeSelector />
              <button onClick={() => router.push('/courses')} className="px-2 py-1 text-xs" style={{ background: 'var(--background-secondary)', color: 'var(--foreground-secondary)', borderRadius: 'var(--radius-sm)' }}>
                返回课程
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="flex-1 flex flex-col overflow-hidden px-2 sm:px-3 py-3">
        <button onClick={() => router.push(`/chapters?course_id=${courseId}`)} className="text-sm flex items-center gap-1 mb-3 flex-shrink-0" style={{ color: 'var(--primary)' }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          返回章节列表
        </button>

        <div className="flex-1 flex gap-4 min-h-0">
          <div className="flex-[3] lg:flex-[4] flex flex-col min-w-0 overflow-hidden" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
            <div className="px-4 sm:px-6 py-3 flex-shrink-0 border-b" style={{ borderColor: 'var(--card-border)' }}>
              <div className="flex items-center justify-between">
                <h1 className="text-lg font-bold truncate" style={{ color: 'var(--foreground-title)' }}>{currentChapter?.title}</h1>
                {currentChapter?.user_progress && (
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <div className="h-1.5 w-24 rounded-full overflow-hidden" style={{ background: 'var(--background-tertiary)' }}>
                      <div className="h-full rounded-full" style={{ width: `${currentChapter.user_progress.last_percentage}%`, background: 'linear-gradient(90deg, var(--primary), var(--primary-light))' }} />
                    </div>
                    <span className="text-xs" style={{ color: 'var(--primary)' }}>{currentChapter.user_progress.last_percentage.toFixed(0)}%</span>
                    {!currentChapter.user_progress.is_completed && (
                      <button onClick={handleChapterComplete} className="px-3 py-1.5 text-xs text-white" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-sm)' }}>标记完成</button>
                    )}
                    {currentChapter.user_progress.is_completed && (
                      <span className="px-2 py-1 text-xs" style={{ background: 'var(--success-light)', color: 'var(--success-dark)', borderRadius: 'var(--radius-full)' }}>✓ 已完成</span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {currentChapter && (
              <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
                <MarkdownReader
                  content={currentChapter.content_markdown}
                  onProgressChange={handleProgressChange}
                  courseDirName={currentChapter.course_dir_name}
                  chapterPath={currentChapter.file_path}
                />
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0 lg:min-w-[320px] lg:max-w-[380px] flex-shrink-0 overflow-hidden" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
            {user ? (
              <AIAssistant chapterId={currentChapter?.id || ''} userId={user.id} />
            ) : (
              <div className="h-full flex items-center justify-center p-8">
                <p style={{ color: 'var(--foreground-tertiary)' }}>请先登录以使用 AI 助手</p>
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
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--background)' }}><p style={{ color: 'var(--foreground-secondary)' }}>加载中...</p></div>}>
      <LearningPageContent />
    </Suspense>
  );
}
