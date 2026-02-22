'use client';

import { useState, useEffect } from 'react';
import { apiClient, WordcloudData, WordcloudStatus } from '@/lib/api';

interface WordcloudViewerProps {
  courseId: string;
  /** 显示模式：course=课程级，chapter=章节级 */
  mode?: 'course' | 'chapter';
  /** 章节名称（章节模式下必需） */
  chapterName?: string;
  /** 自定义类名 */
  className?: string;
  /** 最大显示词数 */
  maxWords?: number;
}

/**
 * 词云渲染组件
 * 用于用户端展示课程或章节的词云可视化
 */
export default function WordcloudViewer({
  courseId,
  mode = 'course',
  chapterName,
  className = '',
  maxWords = 50,
}: WordcloudViewerProps) {
  const [wordcloud, setWordcloud] = useState<WordcloudData | null>(null);
  const [status, setStatus] = useState<WordcloudStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWordcloud();
  }, [courseId, mode, chapterName]);

  const loadWordcloud = async () => {
    setLoading(true);
    setError(null);

    try {
      // 先检查状态
      const statusData = await apiClient.getCourseWordcloudStatus(courseId);
      setStatus(statusData);

      if (!statusData.has_wordcloud) {
        setWordcloud(null);
        setLoading(false);
        return;
      }

      // 加载词云数据
      let data: WordcloudData | null;
      if (mode === 'chapter' && chapterName) {
        data = await apiClient.getChapterWordcloud(courseId, chapterName);
      } else {
        data = await apiClient.getCourseWordcloud(courseId);
      }

      setWordcloud(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载词云失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载中状态
  if (loading) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-2 rounded-full animate-spin border-primary border-t-transparent" />
          <p className="mt-3 text-sm text-foreground-secondary">加载词云...</p>
        </div>
      </div>
    );
  }

  // 错误状态
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

  // 无词云状态
  if (!wordcloud || !status?.has_wordcloud) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[rgba(139,92,246,0.1)] mb-3">
          <svg className="w-6 h-6 text-[#a78bfa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <p className="text-sm text-foreground-secondary">暂无词云数据</p>
        <p className="text-xs text-foreground-tertiary mt-1">词云需要由管理员生成</p>
      </div>
    );
  }

  // 计算词云显示
  const words = wordcloud.words.slice(0, maxWords);
  const maxWeight = Math.max(...words.map(w => w.weight));

  // 词云颜色配置
  const colors = [
    '#8b5cf6', // purple
    '#06b6d4', // cyan
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#ec4899', // pink
    '#3b82f6', // blue
    '#84cc16', // lime
  ];

  return (
    <div className={`${className}`}>
      {/* 词云主体 */}
      <div className="relative p-6 rounded-xl bg-card-bg border border-card-border">
        <div className="flex flex-wrap gap-2 justify-center items-center">
          {words.map((word, index) => {
            // 根据权重计算字体大小和透明度
            const normalizedWeight = word.weight / maxWeight;
            const fontSize = 14 + normalizedWeight * 28; // 14px - 42px
            const opacity = 0.5 + normalizedWeight * 0.5; // 0.5 - 1.0
            const color = colors[index % colors.length];

            return (
              <span
                key={`${word.word}-${index}`}
                style={{
                  fontSize: `${fontSize}px`,
                  opacity,
                  color,
                  fontWeight: normalizedWeight > 0.7 ? 'bold' : 'normal',
                }}
                className="transition-all hover:scale-110 cursor-default select-none"
                title={`${word.word}: ${(word.weight * 100).toFixed(1)}%`}
              >
                {word.word}
              </span>
            );
          })}
        </div>

        {/* 统计信息 */}
        <div className="mt-4 pt-4 border-t border-card-border flex justify-center gap-6 text-xs text-foreground-tertiary">
          <span>共 {wordcloud.words.length} 个关键词</span>
          <span>•</span>
          <span>
            生成于 {new Date(wordcloud.generated_at).toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </span>
        </div>
      </div>

      {/* 详细统计（可折叠） */}
      <details className="mt-3">
        <summary className="cursor-pointer text-sm text-foreground-secondary hover:text-foreground">
          查看详细统计
        </summary>
        <div className="mt-2 p-3 rounded-lg bg-[rgba(255,255,255,0.02)] text-xs text-foreground-tertiary space-y-1">
          <p>总字符数: {wordcloud.source_stats.total_chars.toLocaleString()}</p>
          <p>独立词汇数: {wordcloud.source_stats.unique_words.toLocaleString()}</p>
          <p>提取关键词数: {wordcloud.source_stats.top_words_count}</p>
          {wordcloud.source_stats.total_files && (
            <p>源文件数: {wordcloud.source_stats.total_files}</p>
          )}
        </div>
      </details>
    </div>
  );
}
