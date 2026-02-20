'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient, Course, User } from '@/lib/api';
import Link from 'next/link';
import ThemeSelector from '@/components/ThemeSelector';

function ChaptersPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const courseId = searchParams.get('course_id');

  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      apiClient.getUser(savedUserId).then(setUser);
    }
  }, []);

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

  const handleChapterSelect = (chapterId: string) => {
    router.push(`/learning?course_id=${courseId}&chapter_id=${chapterId}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-2 rounded-full animate-spin border-card-border border-t-primary" />
          <p className="mt-4 text-foreground-secondary">加载中...</p>
        </div>
      </div>
    );
  }

  if (error || !course) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-background">
        <div className="text-center max-w-md p-8 bg-card-bg border border-card-border rounded-lg">
          <p className="mb-4 text-error">{error || '课程不存在'}</p>
          <button onClick={() => router.push('/courses')} className="px-6 py-2 text-white bg-primary rounded-md">
            返回课程列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="sticky top-0 z-50 border-b bg-card-bg border-card-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-14">
            <div className="flex items-center gap-2">
              <Link href="/" className="w-8 h-8 flex items-center justify-center bg-gradient-to-br from-primary to-primary-light rounded-sm">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </Link>
              <span className="text-foreground-tertiary">/</span>
              <Link href="/courses" className="text-foreground-title hover:text-primary transition-colors">选择课程</Link>
              <span className="text-foreground-tertiary">/</span>
              <span className="text-foreground-secondary">{course.title}</span>
            </div>
            <div className="flex items-center gap-3">
              <ThemeSelector />
              {user && <span className="hidden sm:block text-sm text-foreground-secondary">{user.nickname || user.username}</span>}
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2 text-foreground-title">选择章节</h1>
          <p className="text-foreground-secondary">请选择要学习的章节</p>
        </div>

        {chapters.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                onClick={() => handleChapterSelect(chapter.id)}
                className="p-5 cursor-pointer group bg-card-bg border border-card-border rounded-lg hover:border-primary transition-colors"
              >
                <div className="flex items-start gap-4">
                  <span className="flex-shrink-0 w-10 h-10 flex items-center justify-center font-bold bg-gradient-to-br from-primary to-primary-light text-white rounded-sm">
                    {chapter.sort_order}
                  </span>
                  <div className="flex-1 min-w-0">
                    <h2 className="font-semibold truncate text-foreground-title">{chapter.title}</h2>
                    <p className={`text-sm mt-1 ${chapter.user_progress ? 'text-success' : 'text-foreground-tertiary'}`}>
                      {chapter.user_progress ? `已完成 ${chapter.user_progress.last_percentage.toFixed(0)}%` : '未开始'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-card-bg border border-card-border rounded-lg">
            <p className="text-foreground-secondary">暂无可用章节</p>
          </div>
        )}

        <button onClick={() => router.push('/courses')} className="mt-8 flex items-center gap-1 text-sm text-primary hover:text-primary-light transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          返回课程列表
        </button>
      </div>
    </div>
  );
}

export default function ChaptersPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-background"><p className="text-foreground-secondary">加载中...</p></div>}>
      <ChaptersPageContent />
    </Suspense>
  );
}
