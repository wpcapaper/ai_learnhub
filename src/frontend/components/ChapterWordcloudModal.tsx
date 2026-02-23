'use client';

import { useState, useEffect } from 'react';
import { apiClient, WordcloudStatus } from '@/lib/api';
import WordcloudViewer from './WordcloudViewer';

interface ChapterWordcloudModalProps {
  courseId: string;
  chapterId: string;
  chapterTitle: string;
  onClose: () => void;
}

export default function ChapterWordcloudModal({
  courseId,
  chapterId,
  chapterTitle,
  onClose,
}: ChapterWordcloudModalProps) {
  const [status, setStatus] = useState<WordcloudStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.getChapterWordcloudStatus(courseId, chapterId)
      .then(setStatus)
      .finally(() => setLoading(false));
  }, [courseId, chapterId]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div 
        className="w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-xl"
        style={{ 
          background: 'var(--card-bg)', 
          border: '1px solid var(--card-border)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
        }}
      >
        {/* Header */}
        <div 
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: 'var(--card-border)' }}
        >
          <div>
            <h2 className="font-semibold text-base" style={{ color: 'var(--foreground-title)' }}>
              📊 章节词云
            </h2>
            <p className="text-sm mt-0.5" style={{ color: 'var(--foreground-secondary)' }}>
              {chapterTitle}
            </p>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 rounded-lg transition-colors hover:bg-white/10"
            style={{ color: 'var(--foreground-secondary)' }}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto" style={{ maxHeight: 'calc(85vh - 70px)' }}>
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="inline-block h-8 w-8 border-2 rounded-full animate-spin border-violet-500 border-t-transparent" />
                <p className="mt-3 text-sm" style={{ color: 'var(--foreground-secondary)' }}>检查词云状态...</p>
              </div>
            </div>
          ) : status?.has_wordcloud ? (
            <div className="p-4">
              <WordcloudViewer
                courseId={courseId}
                mode="chapter"
                chapterId={chapterId}
                className="h-[400px]"
              />
            </div>
          ) : (
            <div className="text-center py-16 px-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-violet-500/10 to-cyan-500/10 mb-4">
                <svg className="w-8 h-8 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <p className="text-base font-medium" style={{ color: 'var(--foreground)' }}>
                暂无章节词云
              </p>
              <p className="text-sm mt-2" style={{ color: 'var(--foreground-secondary)' }}>
                词云需要由管理员在管理端生成
              </p>
              <button
                onClick={onClose}
                className="mt-6 px-4 py-2 text-sm rounded-lg transition-colors"
                style={{ 
                  background: 'var(--background-secondary)', 
                  color: 'var(--foreground)' 
                }}
              >
                关闭
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
