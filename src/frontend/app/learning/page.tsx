'use client';

import { useState, useEffect, useCallback, Suspense, useRef, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Panel, Group, Separator } from 'react-resizable-panels';
import { apiClient } from '@/lib/api';
import type { Course, User, Chapter } from '@/lib/api';
import MarkdownReader, { MarkdownReaderRef } from '@/components/MarkdownReader';
import AIAssistant from '@/components/AIAssistant';
import ThemeSelector from '@/components/ThemeSelector';
import ContentStats from '@/components/ContentStats';
import OutlineNav from '@/components/OutlineNav';

function LearningPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const courseId = searchParams.get('course_id');
  const initialChapterId = searchParams.get('chapter_id');

  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentChapter, setCurrentChapter] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // 阅读进度（只在章节切换时更新 state，滚动时用 ref）
  const [readingProgress, setReadingProgress] = useState(0);
  const readingProgressRef = useRef(0);
  
  // MarkdownReader 组件引用
  const markdownReaderRef = useRef<MarkdownReaderRef>(null);
  
  // 滚动容器
  const [scrollContainer, setScrollContainer] = useState<HTMLDivElement | null>(null);
  
  // 保存上一个章节 ID，用于同步进度
  const prevChapterIdRef = useRef<string | null>(null);
  
  // 同步指定章节的进度到后端
  const syncProgressToBackend = useCallback(async (chapterId: string, userId: string) => {
    const progressKey = `chapter_progress_${chapterId}`;
    const saved = localStorage.getItem(progressKey);
    
    if (saved) {
      try {
        const { position, percentage } = JSON.parse(saved);
        await apiClient.updateReadingProgress(
          chapterId,
          userId,
          { position, percentage }
        );
      } catch (err) {
        console.error('同步进度失败:', err);
      }
    }
  }, []);
  
  // 更新进度条 UI（直接操作 DOM，避免触发重渲染）
  const updateProgressBar = useCallback((percentage: number) => {
    readingProgressRef.current = percentage;
    const bar = document.getElementById('reading-progress-bar');
    const text = document.getElementById('reading-progress-text');
    if (bar) {
      bar.style.width = `${percentage}%`;
    }
    if (text) {
      text.textContent = `${percentage.toFixed(0)}%`;
    }
  }, []);
  
  // 当 currentChapter 变化时，获取滚动容器
  useEffect(() => {
    if (!currentChapter) return;
    
    // 同步上一个章节的进度
    if (prevChapterIdRef.current && user) {
      syncProgressToBackend(prevChapterIdRef.current, user.id);
    }
    
    // 更新 ref
    prevChapterIdRef.current = currentChapter.id;
    
    setScrollContainer(null);
    
    // 章节切换时更新进度 state（只在这里更新 state）
    const savedProgress = currentChapter.user_progress?.last_percentage || 0;
    setReadingProgress(savedProgress);
    updateProgressBar(savedProgress);
    
    let attempts = 0;
    const maxAttempts = 30;
    
    const tryGetContainer = () => {
      const container = markdownReaderRef.current?.getScrollContainer() || null;
      if (container) {
        setScrollContainer(container);
      } else if (attempts < maxAttempts) {
        attempts++;
        setTimeout(tryGetContainer, 100);
      }
    };
    
    const timer = setTimeout(tryGetContainer, 200);
    
    return () => clearTimeout(timer);
  }, [currentChapter?.id, user, syncProgressToBackend, updateProgressBar]);
  
  // 计算上一章和下一章信息
  const { prevChapter, nextChapter } = useMemo(() => {
    if (!chapters.length || !currentChapter) {
      return { prevChapter: null, nextChapter: null };
    }
    
    const currentIndex = chapters.findIndex(ch => ch.id === currentChapter.id);
    
    return {
      prevChapter: currentIndex > 0 ? chapters[currentIndex - 1] : null,
      nextChapter: currentIndex < chapters.length - 1 ? chapters[currentIndex + 1] : null,
    };
  }, [chapters, currentChapter]);

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
        setChapters(chaptersData);

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

  const handleChapterChange = useCallback((chapterId: string) => {
    router.push(`/learning?course_id=${courseId}&chapter_id=${chapterId}`);
  }, [router, courseId]);

  const handleProgressChange = useCallback(async (position: number, percentage: number) => {
    // 直接更新 DOM，不触发 state 更新
    updateProgressBar(percentage);
    
    if (currentChapter) {
      const progressKey = `chapter_progress_${currentChapter.id}`;
      localStorage.setItem(progressKey, JSON.stringify({
        position,
        percentage,
        timestamp: Date.now(),
      }));
    }
  }, [currentChapter, updateProgressBar]);
  
  // 页面离开时同步进度
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (prevChapterIdRef.current && user) {
        syncProgressToBackend(prevChapterIdRef.current, user.id);
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [user, syncProgressToBackend]);

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

        <Group orientation="horizontal" className="flex-1 min-h-0">
          {/* 左侧大纲导航 - 大屏幕显示 */}
          <Panel defaultSize="15%" minSize="10%" maxSize="25%" className="hidden lg:block">
            <div 
              className="h-full flex flex-col"
              style={{ 
                background: 'var(--card-bg)',
                border: '1px solid var(--card-border)',
                borderRadius: 'var(--radius-lg)',
              }}
            >
              {currentChapter?.content_markdown && scrollContainer && (
                <OutlineNav 
                  key={currentChapter.id}
                  content={currentChapter.content_markdown}
                  scrollContainer={scrollContainer}
                />
              )}
            </div>
          </Panel>
          
          <Separator className="hidden lg:block w-1.5 hover:bg-primary/30 transition-colors" style={{ background: 'var(--card-border)' }} />

          {/* 中间内容区域 */}
          <Panel minSize="30%">
            <div className="h-full flex flex-col overflow-hidden" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 'var(--radius-lg)' }}>
              {/* 章节标题和统计信息 */}
              <div className="px-4 sm:px-6 py-3 flex-shrink-0 border-b" style={{ borderColor: 'var(--card-border)' }}>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <h1 className="text-lg font-bold truncate" style={{ color: 'var(--foreground-title)' }}>{currentChapter?.title}</h1>
                    {currentChapter?.user_progress && (
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <div className="h-1.5 w-24 rounded-full overflow-hidden" style={{ background: 'var(--background-tertiary)' }}>
                          <div id="reading-progress-bar" className="h-full rounded-full" style={{ width: `${readingProgress}%`, background: 'linear-gradient(90deg, var(--primary), var(--primary-light))' }} />
                        </div>
                        <span id="reading-progress-text" className="text-xs" style={{ color: 'var(--primary)' }}>{readingProgress.toFixed(0)}%</span>
                        {!currentChapter.user_progress.is_completed && (
                          <button onClick={handleChapterComplete} className="px-3 py-1.5 text-xs text-white" style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-light))', borderRadius: 'var(--radius-sm)' }}>标记完成</button>
                        )}
                        {currentChapter.user_progress.is_completed && (
                          <span className="px-2 py-1 text-xs" style={{ background: 'var(--success-light)', color: 'var(--success-dark)', borderRadius: 'var(--radius-full)' }}>✓ 已完成</span>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {currentChapter?.content_markdown && (
                    <div className="flex items-center justify-between">
                      <ContentStats content={currentChapter.content_markdown} />
                      <span className="text-xs" style={{ color: 'var(--foreground-tertiary)' }}>
                        章节 {currentChapter?.sort_order || 1} / {chapters.length}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Markdown 内容 */}
              {currentChapter && (
                <MarkdownReader
                  ref={markdownReaderRef}
                  content={currentChapter.content_markdown}
                  onProgressChange={handleProgressChange}
                  courseDirName={currentChapter.course_dir_name}
                  chapterPath={currentChapter.file_path}
                />
              )}

              {/* 章节导航 - 上一章/下一章 */}
              <div 
                className="flex-shrink-0 border-t px-4 sm:px-6 py-3 flex items-center justify-between"
                style={{ borderColor: 'var(--card-border)' }}
              >
                <button
                  onClick={() => prevChapter && handleChapterChange(prevChapter.id)}
                  disabled={!prevChapter}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors"
                  style={{ 
                    color: prevChapter ? 'var(--primary)' : 'var(--foreground-tertiary)',
                    background: prevChapter ? 'var(--primary-bg)' : 'var(--background-secondary)',
                    borderRadius: 'var(--radius-sm)',
                    cursor: prevChapter ? 'pointer' : 'not-allowed',
                    opacity: prevChapter ? 1 : 0.5,
                  }}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  <span className="hidden sm:inline">上一章</span>
                  {prevChapter && <span className="hidden md:inline truncate max-w-[120px]">: {prevChapter.title}</span>}
                </button>
                
                <span className="text-xs px-2" style={{ color: 'var(--foreground-tertiary)' }}>
                  {chapters.findIndex(ch => ch.id === currentChapter?.id) + 1} / {chapters.length}
                </span>
                
                <button
                  onClick={() => nextChapter && handleChapterChange(nextChapter.id)}
                  disabled={!nextChapter}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors"
                  style={{ 
                    color: nextChapter ? 'var(--primary)' : 'var(--foreground-tertiary)',
                    background: nextChapter ? 'var(--primary-bg)' : 'var(--background-secondary)',
                    borderRadius: 'var(--radius-sm)',
                    cursor: nextChapter ? 'pointer' : 'not-allowed',
                    opacity: nextChapter ? 1 : 0.5,
                  }}
                >
                  {nextChapter && <span className="hidden md:inline truncate max-w-[120px]">{nextChapter.title}: </span>}
                  <span className="hidden sm:inline">下一章</span>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          </Panel>

          <Separator className="hidden lg:block w-1.5 hover:bg-primary/30 transition-colors" style={{ background: 'var(--card-border)' }} />
          
          {/* 右侧 AI 助手 */}
          <Panel defaultSize="28%" minSize="20%" maxSize="40%" className="hidden lg:block">
            <div 
              className="h-full flex flex-col overflow-hidden"
              style={{ 
                background: 'var(--card-bg)', 
                border: '1px solid var(--card-border)', 
                borderRadius: 'var(--radius-lg)' 
              }}
            >
              {user ? (
                <AIAssistant chapterId={currentChapter?.id || ''} userId={user.id} />
              ) : (
                <div className="h-full flex items-center justify-center p-8">
                  <p style={{ color: 'var(--foreground-tertiary)' }}>请先登录以使用 AI 助手</p>
                </div>
              )}
            </div>
          </Panel>
        </Group>
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
