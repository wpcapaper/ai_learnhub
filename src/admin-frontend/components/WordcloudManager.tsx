'use client';

import { useState, useEffect } from 'react';
import { 
  adminApi, 
  WordcloudData, 
  WordcloudStatus,
  ChapterWordcloudStatus 
} from '@/lib/api';

interface WordcloudManagerProps {
  courseId: string;
  courseName: string;
  onClose: () => void;
}

export default function WordcloudManager({ 
  courseId, 
  courseName, 
  onClose 
}: WordcloudManagerProps) {
  const [loading, setLoading] = useState(false);
  const [courseWordcloud, setCourseWordcloud] = useState<WordcloudData | null>(null);
  const [courseStatus, setCourseStatus] = useState<WordcloudStatus | null>(null);
  const [chapters, setChapters] = useState<ChapterWordcloudStatus[]>([]);
  const [activeTab, setActiveTab] = useState<'course' | 'chapters'>('course');
  const [selectedChapter, setSelectedChapter] = useState<string | null>(null);
  const [chapterWordcloud, setChapterWordcloud] = useState<WordcloudData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 加载词云状态
  useEffect(() => {
    loadWordcloudStatus();
    loadChaptersStatus();
  }, [courseId]);

  const loadWordcloudStatus = async () => {
    const response = await adminApi.getCourseWordcloudStatus(courseId);
    if (response.success && response.data) {
      setCourseStatus(response.data);
      if (response.data.has_wordcloud) {
        loadCourseWordcloud();
      }
    }
  };

  const loadCourseWordcloud = async () => {
    const response = await adminApi.getCourseWordcloud(courseId);
    if (response.success && response.data) {
      setCourseWordcloud(response.data);
    }
  };

  const loadChaptersStatus = async () => {
    const response = await adminApi.listChapterWordcloudStatus(courseId);
    if (response.success && response.data) {
      setChapters(response.data);
    }
  };

  // 生成课程词云
  const handleGenerateCourseWordcloud = async () => {
    setLoading(true);
    setError(null);
    
    const response = await adminApi.generateCourseWordcloud(courseId);
    
    if (response.success && response.data) {
      setCourseWordcloud(response.data.data);
      setCourseStatus({
        has_wordcloud: true,
        generated_at: response.data.data.generated_at,
        words_count: response.data.data.words.length
      });
    } else {
      setError(response.error || '生成失败');
    }
    
    setLoading(false);
  };

  // 批量生成所有词云
  const handleBatchGenerate = async () => {
    setLoading(true);
    setError(null);
    
    const response = await adminApi.batchGenerateWordclouds(courseId);
    
    if (response.success && response.data) {
      if (response.data.course_wordcloud) {
        setCourseWordcloud(response.data.course_wordcloud);
        setCourseStatus({
          has_wordcloud: true,
          generated_at: response.data.course_wordcloud.generated_at,
          words_count: response.data.course_wordcloud.words.length
        });
      }
      loadChaptersStatus();
    } else {
      setError(response.error || '批量生成失败');
    }
    
    setLoading(false);
  };

  // 删除课程词云
  const handleDeleteCourseWordcloud = async () => {
    if (!confirm('确定要删除课程词云吗？')) return;
    
    setLoading(true);
    const response = await adminApi.deleteCourseWordcloud(courseId);
    
    if (response.success) {
      setCourseWordcloud(null);
      setCourseStatus({ has_wordcloud: false, generated_at: null, words_count: 0 });
    } else {
      setError(response.error || '删除失败');
    }
    
    setLoading(false);
  };

  // 生成章节词云
  const handleGenerateChapterWordcloud = async (chapterName: string) => {
    setLoading(true);
    setError(null);
    
    const response = await adminApi.generateChapterWordcloud(courseId, chapterName);
    
    if (response.success && response.data) {
      setChapterWordcloud(response.data.data);
      loadChaptersStatus();
    } else {
      setError(response.error || '生成失败');
    }
    
    setLoading(false);
  };

  // 加载章节词云
  const handleViewChapterWordcloud = async (chapterName: string) => {
    setLoading(true);
    setSelectedChapter(chapterName);
    
    const response = await adminApi.getChapterWordcloud(courseId, chapterName);
    
    if (response.success && response.data) {
      setChapterWordcloud(response.data);
    } else {
      setChapterWordcloud(null);
    }
    
    setLoading(false);
  };

  // 词云预览组件
  const WordcloudPreview = ({ data }: { data: WordcloudData }) => {
    const maxWeight = Math.max(...data.words.map(w => w.weight));
    
    return (
      <div className="mt-4 p-4 rounded-lg bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)]">
        <div className="flex flex-wrap gap-2 justify-center">
          {data.words.slice(0, 30).map((word, index) => {
            const fontSize = 12 + (word.weight / maxWeight) * 24;
            const opacity = 0.5 + (word.weight / maxWeight) * 0.5;
            const colors = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];
            const color = colors[index % colors.length];
            
            return (
              <span
                key={index}
                style={{
                  fontSize: `${fontSize}px`,
                  opacity,
                  color,
                  fontWeight: word.weight > maxWeight * 0.7 ? 'bold' : 'normal',
                }}
                className="transition-all hover:scale-110 cursor-default"
              >
                {word.word}
              </span>
            );
          })}
        </div>
        <div className="mt-4 text-xs text-center text-[#71717a]">
          共 {data.words.length} 个关键词 | 
          生成时间: {new Date(data.generated_at).toLocaleString()}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[#18181b] rounded-xl border border-[rgba(255,255,255,0.06)] w-full max-w-3xl max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-[rgba(255,255,255,0.06)]">
          <div>
            <h2 className="text-lg font-semibold text-[#fafafa]">
              📊 词云管理
            </h2>
            <p className="text-sm text-[#71717a]">{courseName}</p>
          </div>
          <button
            onClick={onClose}
            className="text-[#71717a] hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mx-4 mt-4 p-3 rounded-lg bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)] text-[#f87171] text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-2 underline">关闭</button>
          </div>
        )}

        {/* Tab 切换 */}
        <div className="flex gap-2 p-4 border-b border-[rgba(255,255,255,0.06)]">
          <button
            onClick={() => setActiveTab('course')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'course'
                ? 'bg-[rgba(139,92,246,0.15)] text-[#a78bfa]'
                : 'text-[#71717a] hover:text-[#a1a1aa]'
            }`}
          >
            课程词云
          </button>
          <button
            onClick={() => setActiveTab('chapters')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'chapters'
                ? 'bg-[rgba(139,92,246,0.15)] text-[#a78bfa]'
                : 'text-[#71717a] hover:text-[#a1a1aa]'
            }`}
          >
            章节词云
          </button>
        </div>

        {/* 内容区 */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#667eea] border-t-transparent" />
            </div>
          )}

          {!loading && activeTab === 'course' && (
            <div>
              {/* 课程词云状态和操作 */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  {courseStatus?.has_wordcloud ? (
                    <div className="text-sm">
                      <span className="text-[#4ade80]">✓ 已生成</span>
                      <span className="text-[#71717a] ml-2">
                        {courseStatus.words_count} 个关键词
                      </span>
                    </div>
                  ) : (
                    <span className="text-sm text-[#71717a]">未生成</span>
                  )}
                </div>
                <div className="flex gap-2">
                  {courseStatus?.has_wordcloud && (
                    <button
                      onClick={handleDeleteCourseWordcloud}
                      disabled={loading}
                      className="px-3 py-1.5 text-sm rounded-lg bg-[rgba(239,68,68,0.1)] text-[#f87171] hover:bg-[rgba(239,68,68,0.2)] transition-colors"
                    >
                      删除
                    </button>
                  )}
                  <button
                    onClick={handleGenerateCourseWordcloud}
                    disabled={loading}
                    className="px-3 py-1.5 text-sm rounded-lg bg-gradient-to-r from-[#667eea] to-[#764ba2] text-white hover:opacity-90 transition-opacity"
                  >
                    {courseStatus?.has_wordcloud ? '重新生成' : '生成词云'}
                  </button>
                  <button
                    onClick={handleBatchGenerate}
                    disabled={loading}
                    className="px-3 py-1.5 text-sm rounded-lg bg-[rgba(6,182,212,0.1)] text-[#22d3ee] hover:bg-[rgba(6,182,212,0.2)] transition-colors"
                  >
                    全部生成
                  </button>
                </div>
              </div>

              {/* 词云预览 */}
              {courseWordcloud && (
                <WordcloudPreview data={courseWordcloud} />
              )}
            </div>
          )}

          {!loading && activeTab === 'chapters' && (
            <div>
              {/* 章节列表 */}
              <div className="flex justify-end mb-4">
                <button
                  onClick={handleBatchGenerate}
                  disabled={loading}
                  className="px-3 py-1.5 text-sm rounded-lg bg-gradient-to-r from-[#667eea] to-[#764ba2] text-white hover:opacity-90 transition-opacity"
                >
                  全部生成
                </button>
              </div>

              <div className="space-y-2">
                {chapters.map((chapter) => (
                  <div
                    key={chapter.name}
                    className="flex items-center justify-between p-3 rounded-lg bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)]"
                  >
                    <div className="flex items-center gap-3">
                      <span className={chapter.has_wordcloud ? 'text-[#4ade80]' : 'text-[#71717a]'}>
                        {chapter.has_wordcloud ? '✓' : '○'}
                      </span>
                      <span className="text-sm text-[#fafafa]">{chapter.name}</span>
                    </div>
                    <div className="flex gap-2">
                      {chapter.has_wordcloud && (
                        <button
                          onClick={() => handleViewChapterWordcloud(chapter.name)}
                          className="px-2 py-1 text-xs rounded bg-[rgba(255,255,255,0.05)] text-[#a1a1aa] hover:bg-[rgba(255,255,255,0.1)] transition-colors"
                        >
                          查看
                        </button>
                      )}
                      <button
                        onClick={() => handleGenerateChapterWordcloud(chapter.name)}
                        disabled={loading}
                        className="px-2 py-1 text-xs rounded bg-[rgba(139,92,246,0.1)] text-[#a78bfa] hover:bg-[rgba(139,92,246,0.2)] transition-colors"
                      >
                        {chapter.has_wordcloud ? '重新生成' : '生成'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* 选中章节的词云预览 */}
              {selectedChapter && chapterWordcloud && (
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-[#fafafa] mb-2">
                    {selectedChapter}
                  </h3>
                  <WordcloudPreview data={chapterWordcloud} />
                </div>
              )}

              {chapters.length === 0 && (
                <div className="text-center py-8 text-[#71717a]">
                  暂无章节数据
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
