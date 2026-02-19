'use client';

import { useState, useEffect } from 'react';
import { adminApi, Course } from '@/lib/api';

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [converting, setConverting] = useState(false);

  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    setLoading(true);
    const response = await adminApi.getCourses();
    if (response.success && response.data) {
      setCourses(response.data);
    }
    setLoading(false);
  };

  const handleConvert = async () => {
    setConverting(true);
    const response = await adminApi.convertCourses();
    setConverting(false);
    
    if (response.success) {
      loadCourses();
    } else {
      alert(`转换失败: ${response.error}`);
    }
  };

  const stats = {
    total: courses.length,
    chapters: courses.reduce((sum, c) => sum + (c.chapters?.length || 0), 0),
    avgQuality: courses.filter(c => c.quality_score).length > 0
      ? Math.round(courses.filter(c => c.quality_score).reduce((sum, c) => sum + (c.quality_score || 0), 0) / courses.filter(c => c.quality_score).length)
      : 0,
    evaluated: courses.filter(c => c.quality_score).length,
  };

  if (loading) {
    return <LoadingSkeleton />;
  }

  return (
    <div className="p-8">
      {/* 页面头部 */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-[11px] text-[#71717a] mb-2">
          <span>知识库</span>
          <svg style={{width: '12px', height: '12px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-[#a1a1aa]">课程管理</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[#fafafa] mb-1">课程管理</h1>
            <p className="text-sm text-[#71717a]">管理课程内容转换与 RAG 索引优化</p>
          </div>
          <div className="flex gap-2">
            <button onClick={loadCourses} className="btn btn-secondary">
              <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              刷新
            </button>
            <button onClick={handleConvert} disabled={converting} className="btn btn-primary">
              {converting ? (
                <>
                  <svg style={{width: '14px', height: '14px'}} className="icon-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  转换中...
                </>
              ) : (
                <>
                  <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  转换课程
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="总课程" value={stats.total} icon="book" gradient />
        <StatCard label="总章节" value={stats.chapters} icon="folder" />
        <StatCard label="平均质量" value={stats.avgQuality || '-'} icon="chart" highlight={stats.avgQuality >= 80} />
        <StatCard label="已评估" value={`${stats.evaluated}/${stats.total}`} icon="check" />
      </div>

      {/* 课程列表 */}
      {courses.length === 0 ? (
        <EmptyState onConvert={handleConvert} converting={converting} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {courses.map(course => (
            <CourseCard key={course.id} course={course} />
          ))}
        </div>
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="p-8">
      <div className="animate-pulse">
        <div className="h-6 w-32 bg-[rgba(255,255,255,0.05)] rounded mb-2" />
        <div className="h-4 w-48 bg-[rgba(255,255,255,0.03)] rounded mb-8" />
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-[rgba(255,255,255,0.03)] rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-40 bg-[rgba(255,255,255,0.03)] rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, gradient, highlight }: { 
  label: string; 
  value: string | number; 
  icon: string;
  gradient?: boolean;
  highlight?: boolean;
}) {
  const icons: Record<string, React.ReactNode> = {
    book: (
      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
    folder: (
      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
      </svg>
    ),
    chart: (
      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    check: (
      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  return (
    <div className={`metric-card ${gradient ? 'bg-gradient-to-br from-[#18181b] to-[rgba(139,92,246,0.08)]' : ''}`}>
      <div className="flex items-center justify-between mb-3">
        <div className={`p-2 rounded-lg ${gradient ? 'bg-[rgba(139,92,246,0.15)] text-[#a78bfa]' : 'bg-[rgba(255,255,255,0.05)] text-[#71717a]'}`}>
          {icons[icon]}
        </div>
      </div>
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${gradient ? 'gradient-text' : ''} ${highlight ? 'text-[#4ade80]' : ''}`}>
        {value}
      </div>
    </div>
  );
}

function EmptyState({ onConvert, converting }: { onConvert: () => void; converting: boolean }) {
  return (
    <div className="card p-12 text-center">
      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-[rgba(139,92,246,0.2)] to-[rgba(6,182,212,0.1)] flex items-center justify-center">
        <svg style={{width: '28px', height: '28px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} className="text-[#a78bfa]">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-[#fafafa] mb-2">暂无课程数据</h3>
      <p className="text-sm text-[#71717a] mb-6 max-w-xs mx-auto">
        点击下方按钮导入课程内容，开始构建知识库
      </p>
      <button onClick={onConvert} disabled={converting} className="btn btn-primary">
        {converting ? '转换中...' : (
          <>
            <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            导入课程
          </>
        )}
      </button>
    </div>
  );
}

function CourseCard({ course }: { course: Course }) {
  const score = course.quality_score;
  const hasScore = score !== undefined && score !== null;
  const scoreLevel = hasScore ? (score! >= 80 ? 'high' : score! >= 60 ? 'medium' : 'low') : 'none';
  
  const scoreColors = {
    high: { text: 'text-[#4ade80]', bg: 'bg-[rgba(34,197,94,0.1)]', border: 'border-[rgba(34,197,94,0.2)]' },
    medium: { text: 'text-[#fbbf24]', bg: 'bg-[rgba(245,158,11,0.1)]', border: 'border-[rgba(245,158,11,0.2)]' },
    low: { text: 'text-[#f87171]', bg: 'bg-[rgba(239,68,68,0.1)]', border: 'border-[rgba(239,68,68,0.2)]' },
    none: { text: 'text-[#71717a]', bg: 'bg-[rgba(255,255,255,0.03)]', border: 'border-transparent' },
  };

  return (
    <div className="card card-glow p-5 group">
      {/* 头部 */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-[rgba(139,92,246,0.1)] text-[#a78bfa] border border-[rgba(139,92,246,0.2)]">
              {course.code}
            </span>
            {hasScore && (
              <span className={`tag ${score! >= 80 ? 'tag-success' : score! >= 60 ? 'tag-warning' : 'tag-error'}`}>
                已评估
              </span>
            )}
          </div>
          <h3 className="text-[15px] font-medium text-[#fafafa] truncate">{course.title}</h3>
        </div>
        
        {/* 质量分数 */}
        <div className={`flex flex-col items-end px-3 py-1.5 rounded-lg ${scoreColors[scoreLevel].bg} ${scoreColors[scoreLevel].border} border ml-3`}>
          <span className={`text-xl font-bold ${scoreColors[scoreLevel].text}`}>
            {hasScore ? score : '-'}
          </span>
          <span className="text-[9px] text-[#71717a] uppercase tracking-wider">质量分</span>
        </div>
      </div>

      {/* 描述 */}
      <p className="text-xs text-[#71717a] line-clamp-2 mb-4 min-h-[32px]">
        {course.description || '暂无描述'}
      </p>

      {/* 章节信息 */}
      <div className="flex items-center gap-4 text-xs text-[#71717a] mb-4 pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <span className="flex items-center gap-1.5">
          <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {course.chapters?.length || 0} 章节
        </span>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <a 
          href={`/optimization?course=${course.id}`} 
          className="btn btn-secondary flex-1 text-xs"
        >
          <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          RAG 优化
        </a>
        <a 
          href={`/evaluation?course=${course.id}`} 
          className="btn btn-ghost flex-1 text-xs"
        >
          <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          查看报告
        </a>
      </div>
    </div>
  );
}
