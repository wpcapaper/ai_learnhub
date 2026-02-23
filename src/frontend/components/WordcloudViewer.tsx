'use client';

import { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { apiClient, WordcloudData, WordcloudStatus } from '@/lib/api';

const ReactWordcloud = dynamic(
  () => import('@cp949/react-wordcloud').then(mod => mod.ReactWordcloud),
  { 
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center py-20">
        <div className="inline-block h-8 w-8 border-2 rounded-full animate-spin border-primary border-t-transparent" />
      </div>
    )
  }
);

interface WordcloudViewerProps {
  courseId: string;
  mode?: 'course' | 'chapter';
  chapterId?: string;  // 章节 UUID（用于 chapter 模式）
  className?: string;
  maxWords?: number;
}

export default function WordcloudViewer({
  courseId,
  mode = 'course',
  chapterId,
  className = '',
  maxWords = 80,
}: WordcloudViewerProps) {
  const [wordcloud, setWordcloud] = useState<WordcloudData | null>(null);
  const [status, setStatus] = useState<WordcloudStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWordcloud();
  }, [courseId, mode, chapterId]);

  const loadWordcloud = async () => {
    setLoading(true);
    setError(null);

    try {
      let statusData: WordcloudStatus;
      let data: WordcloudData | null;

      if (mode === 'chapter' && chapterId) {
        // 章节词云：使用章节 UUID
        statusData = await apiClient.getChapterWordcloudStatus(courseId, chapterId);
        if (statusData.has_wordcloud) {
          data = await apiClient.getChapterWordcloud(courseId, chapterId);
        } else {
          data = null;
        }
      } else {
        // 课程词云
        statusData = await apiClient.getCourseWordcloudStatus(courseId);
        if (statusData.has_wordcloud) {
          data = await apiClient.getCourseWordcloud(courseId);
        } else {
          data = null;
        }
      }

      setStatus(statusData);
      setWordcloud(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载词云失败');
    } finally {
      setLoading(false);
    }
  };

  const words = useMemo(() => {
    if (!wordcloud) return [];
    return wordcloud.words.slice(0, maxWords).map(w => ({
      text: w.word,
      value: Math.round(w.weight * 1000),
    }));
  }, [wordcloud, maxWords]);

  const options = useMemo(() => ({
    fontFamily: 'PingFang SC, Microsoft YaHei, Noto Sans SC, sans-serif',
    fontSizes: [14, 80] as [number, number],
    fontWeight: '700' as const,
    rotations: 1,
    rotationAngles: [-45, 45] as [number, number],
    padding: 3,
    scale: 'linear' as const,
    deterministic: true,
    randomSeed: 'wordcloud-seed-2024' as const,
    spiral: 'archimedean' as const,
    transitionDuration: 500,
    colors: ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#3b82f6', '#ec4899', '#ef4444', '#84cc16'],
  }), []);

  const callbacks = useMemo(() => ({
    getWordTooltip: (word: { text: string; value: number }) => 
      `${word.text}: ${(word.value / 10).toFixed(1)}%`,
    onWordClick: (word: { text: string; value: number }) => {
      console.log('Clicked:', word.text);
    },
  }), []);

  if (loading) {
    return (
      <div className={`flex items-center justify-center py-20 ${className}`}>
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-2 rounded-full animate-spin border-primary border-t-transparent" />
          <p className="mt-3 text-sm text-foreground-secondary">加载词云...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <p className="text-sm text-error">{error}</p>
        <button 
          onClick={loadWordcloud}
          className="mt-2 text-sm text-primary hover:text-primary-light"
        >
          重试
        </button>
      </div>
    );
  }

  if (!wordcloud || !status?.has_wordcloud) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-violet-500/10 to-cyan-500/10 mb-4">
          <svg className="w-8 h-8 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <p className="text-foreground-secondary">暂无词云数据</p>
        <p className="text-xs text-foreground-tertiary mt-1">词云需要由管理员生成</p>
      </div>
    );
  }

  return (
    <div className={`${className}`}>
      <div className="relative rounded-2xl bg-gradient-to-br from-card-bg to-card-bg/50 border border-card-border overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-violet-500/5 via-transparent to-transparent" />
        
        <div className="relative h-[700px] flex items-center justify-center">
          <ReactWordcloud
            words={words}
            options={options}
            callbacks={callbacks}
          />
        </div>

        <div className="relative px-4 py-3 border-t border-card-border/50 bg-gradient-to-r from-transparent via-card-bg/50 to-transparent">
          <div className="flex justify-center gap-6 text-xs text-foreground-tertiary">
            <span className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              {wordcloud.words.length} 个关键词
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {new Date(wordcloud.generated_at).toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </span>
          </div>
        </div>
      </div>

      <details className="mt-4 group">
        <summary className="cursor-pointer text-sm text-foreground-secondary hover:text-foreground transition-colors flex items-center gap-2">
          <svg className="w-4 h-4 transition-transform group-open:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          查看详细统计
        </summary>
        <div className="mt-3 p-4 rounded-xl bg-card-bg/50 border border-card-border/50">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-foreground-tertiary">总字符数:</span>
              <span className="text-foreground font-medium">{wordcloud.source_stats.total_chars.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-foreground-tertiary">独立词汇:</span>
              <span className="text-foreground font-medium">{wordcloud.source_stats.unique_words.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-foreground-tertiary">提取关键词:</span>
              <span className="text-foreground font-medium">{wordcloud.source_stats.top_words_count}</span>
            </div>
            {wordcloud.source_stats.total_files && (
              <div className="flex items-center gap-2">
                <span className="text-foreground-tertiary">源文件数:</span>
                <span className="text-foreground font-medium">{wordcloud.source_stats.total_files}</span>
              </div>
            )}
          </div>
        </div>
      </details>
    </div>
  );
}
