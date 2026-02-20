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
              <span style={{ color: 'var(--foreground-tertiary)' }}>/</span>
              <span style={{ color: 'var(--foreground-secondary)' }}>{course.title}</span>
            </div>
            <div className="flex items-center gap-3">
              <ThemeSelector />
              {user && <span className="hidden sm:block text-sm" style={{ color: 'var(--foreground-secondary)' }}>{user.nickname || user.username}</span>}
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground-title)' }}>选择章节</h1>
          <p style={{ color: 'var(--foreground-secondary)' }}>请选择要学习的章节</p>
        </div>

        {chapters.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                onClick={() => handleChapterSelect(chapter.id)}
                className="p-5 cursor-pointer group"
                style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}
              >
                <div className="flex items-start gap-4">
                  <span className="flex-shrink-0 w-10 h-10 flex items-center justify-center font-bold" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', color: '#fff', borderRadius: 'var(--radius-sm)' }}>
                    {chapter.sort_order}
                  </span>
                  <div className="flex-1 min-w-0">
                    <h2 className="font-semibold truncate" style={{ color: 'var(--foreground-title)' }}>{chapter.title}</h2>
                    <p className="text-sm mt-1" style={{ color: chapter.user_progress ? 'var(--success)' : 'var(--foreground-tertiary)' }}>
                      {chapter.user_progress ? `已完成 ${chapter.user_progress.last_percentage.toFixed(0)}%` : '未开始'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
            <p style={{ color: 'var(--foreground-secondary)' }}>暂无可用章节</p>
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

export default function ChaptersPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--background)' }}><p style={{ color: 'var(--foreground-secondary)' }}>加载中...</p></div>}>
      <ChaptersPageContent />
    </Suspense>
  );
}
