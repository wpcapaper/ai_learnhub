'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import type { Chapter, ChapterContent } from '@/lib/api';

interface ChapterNavigationProps {
  courseId: string;
  currentChapterId?: string;
  chapters: Chapter[];
  onChapterSelect: (chapterId: string) => void;
  progressSummary?: any;
}

export default function ChapterNavigation({ courseId, currentChapterId, chapters, onChapterSelect, progressSummary }: ChapterNavigationProps) {
  return (
    <div 
      className="w-64 p-4 flex flex-col"
      style={{ 
        background: 'var(--card-bg)',
        borderRight: '1px solid var(--card-border)'
      }}
    >
      <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--foreground-title)' }}>章节目录</h2>
      
      {/* 课程进度摘要 */}
      {progressSummary && (
        <div 
          className="mb-4 p-3"
          style={{ 
            background: 'var(--primary-bg)',
            borderRadius: 'var(--radius-md)'
          }}
        >
          <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>
            <span className="font-semibold">进度:</span>{progressSummary.progress_percentage?.toFixed(1)}%
          </p>
          <p className="text-xs" style={{ color: 'var(--foreground-tertiary)' }}>
            {progressSummary.completed_chapters} / {progressSummary.total_chapters} 章节完成
          </p>
        </div>
      )}

      {/* 章节列表 */}
      <div className="flex-1 overflow-y-auto">
        {chapters.map((chapter) => (
          <button
            key={chapter.id}
            onClick={() => onChapterSelect(chapter.id)}
            className="w-full text-left px-4 py-3 mb-2 transition-all"
            style={{ 
              background: currentChapterId === chapter.id ? 'var(--primary)' : 'var(--background-secondary)',
              color: currentChapterId === chapter.id ? '#FFFFFF' : 'var(--foreground-secondary)',
              borderRadius: 'var(--radius-md)'
            }}
          >
            <div className="flex items-start gap-3">
              <span className="flex-1">
                <span className="font-medium">{chapter.sort_order}. {chapter.title}</span>
                {/* 完成标记 */}
                {progressSummary?.completed_chapters && (
                  <span className="ml-2" style={{ color: 'var(--success)' }}>✓</span>
                )}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
