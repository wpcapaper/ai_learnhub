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
    <div className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">章节目录</h2>
      
      {/* 课程进度摘要 */}
      {progressSummary && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg">
          <p className="text-sm text-gray-700">
            <span className="font-semibold">进度:</span>{progressSummary.progress_percentage?.toFixed(1)}%
          </p>
          <p className="text-xs text-gray-600">
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
            className={`w-full text-left px-4 py-3 mb-2 rounded-lg transition-all ${
              currentChapterId === chapter.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-50 hover:bg-gray-100 text-gray-700'
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="flex-1">
                <span className="font-medium">{chapter.sort_order}. {chapter.title}</span>
                {/* 完成标记 */}
                {progressSummary?.completed_chapters && (
                  <span className="ml-2 text-green-600">✓</span>
                )}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
