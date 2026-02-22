'use client';

import { useState, useEffect } from 'react';
import { 
  adminApi, 
  Course, 
  RawCourse, 
  DatabaseCourse,
  ImportResult,
  QuizGenerateResult 
} from '@/lib/api';
import WordcloudManager from '@/components/WordcloudManager';

type TabType = 'converted' | 'raw' | 'database';

type ConvertResult = {
  success: boolean;
  message: string;
  convertedCount: number;
};

export default function CoursesPage() {
  const [activeTab, setActiveTab] = useState<TabType>('converted');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  const [convertedCourses, setConvertedCourses] = useState<Course[]>([]);
  const [rawCourses, setRawCourses] = useState<RawCourse[]>([]);
  const [databaseCourses, setDatabaseCourses] = useState<DatabaseCourse[]>([]);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [quizResult, setQuizResult] = useState<QuizGenerateResult | null>(null);
  const [convertResult, setConvertResult] = useState<ConvertResult | null>(null);
  // 词云弹窗状态
  const [wordcloudModal, setWordcloudModal] = useState<{ courseId: string; courseName: string } | null>(null);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    
    const [convertedRes, rawRes, dbRes] = await Promise.all([
      adminApi.getCourses(),
      adminApi.getRawCourses(),
      adminApi.getDatabaseCourses(),
    ]);
    
    if (convertedRes.success && convertedRes.data) {
      setConvertedCourses(convertedRes.data);
    }
    if (rawRes.success && rawRes.data) {
      setRawCourses(rawRes.data);
    }
    if (dbRes.success && dbRes.data) {
      setDatabaseCourses(dbRes.data);
    }
    
    setLoading(false);
  };

  const handleConvert = async () => {
    setActionLoading('convert');
    setConvertResult(null);
    const response = await adminApi.convertCourses();
    setActionLoading(null);
    
    if (response.success && response.data) {
      const results = response.data.results as Array<{ success: boolean }>;
      const successCount = results.filter(r => r.success).length;
      setConvertResult({
        success: successCount > 0,
        message: response.data.message,
        convertedCount: successCount
      });
      loadAllData();
    } else {
      alert(`转换失败: ${response.error}`);
    }
  };

  const handleConvertSingle = async (courseId: string) => {
    setActionLoading(`convert-${courseId}`);
    setConvertResult(null);
    const response = await adminApi.convertSingleCourse(courseId);
    setActionLoading(null);
    
    if (response.success && response.data) {
      const results = response.data.results as Array<{ success: boolean }>;
      const successCount = results.filter(r => r.success).length;
      setConvertResult({
        success: successCount > 0,
        message: response.data.message,
        convertedCount: successCount
      });
      loadAllData();
    } else {
      alert(`转换失败: ${response.error}`);
    }
  };

  const handleImport = async () => {
    setActionLoading('import');
    setImportResult(null);
    const response = await adminApi.importCoursesToDatabase();
    setActionLoading(null);
    
    if (response.success && response.data) {
      setImportResult(response.data);
      loadAllData();
    } else {
      alert(`导入失败: ${response.error}`);
    }
  };

  const handleImportSingle = async (courseId: string) => {
    setActionLoading(`import-${courseId}`);
    setImportResult(null);
    const response = await adminApi.importSingleCourseToDatabase(courseId);
    setActionLoading(null);
    
    if (response.success && response.data) {
      setImportResult(response.data);
      loadAllData();
    } else {
      alert(`导入失败: ${response.error}`);
    }
  };

  const handleDeleteFromDb = async (courseId: string) => {
    if (!confirm('确定要从数据库删除此课程吗？')) return;
    
    setActionLoading(`delete-${courseId}`);
    const response = await adminApi.deleteCourseFromDatabase(courseId);
    setActionLoading(null);
    
    if (response.success) {
      loadAllData();
    } else {
      alert(`删除失败: ${response.error}`);
    }
  };

  const handleGenerateQuiz = async (courseId: string) => {
    setActionLoading(`quiz-${courseId}`);
    setQuizResult(null);
    const response = await adminApi.generateQuiz(courseId);
    setActionLoading(null);
    
    if (response.success && response.data) {
      setQuizResult(response.data);
    } else {
      alert(`生成失败: ${response.error}`);
    }
  };

  const stats = {
    raw: rawCourses.length,
    converted: convertedCourses.length,
    database: databaseCourses.length,
    chapters: convertedCourses.reduce((sum, c) => sum + (c.chapters?.length || 0), 0),
    dbChapters: databaseCourses.reduce((sum, c) => sum + c.chapter_count, 0),
  };

  if (loading) {
    return <LoadingSkeleton />;
  }

  return (
    <>
    <div className="p-8">
      <div className="mb-8">
        <div className="flex items-center gap-2 text-[13px] text-[#71717a] mb-2">
          <span>知识库</span>
          <svg style={{width: '12px', height: '12px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-[#a1a1aa]">课程管理</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[#fafafa] mb-1">课程管理</h1>
            <p className="text-base text-[#71717a]">管理课程转换与数据库导入</p>
          </div>
          <div className="flex gap-2">
            <button onClick={loadAllData} className="btn btn-secondary">
              <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              刷新
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard 
          label="原始课程" 
          value={stats.raw} 
          icon="inbox" 
          subtitle="raw_courses"
        />
        <StatCard 
          label="已转换" 
          value={stats.converted} 
          icon="folder" 
          gradient
          subtitle={`${stats.chapters} 章节`}
        />
        <StatCard 
          label="已导入" 
          value={stats.database} 
          icon="database" 
          highlight={stats.database > 0}
          subtitle={`${stats.dbChapters} 章节`}
        />
        <StatCard 
          label="待处理" 
          value={stats.raw > 0 ? stats.raw : (stats.converted > stats.database ? stats.converted - stats.database : 0)} 
          icon="clock"
        />
      </div>

      {convertResult && (
        <div className={`mb-6 p-4 rounded-xl border ${convertResult.success ? 'bg-[rgba(34,197,94,0.1)] border-[rgba(34,197,94,0.2)]' : 'bg-[rgba(239,68,68,0.1)] border-[rgba(239,68,68,0.2)]'}`}>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {convertResult.success && (
                <div className="p-2 rounded-lg bg-[rgba(34,197,94,0.15)]">
                  <svg style={{width: '20px', height: '20px'}} fill="none" stroke="#4ade80" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
              <div>
                <h4 className={`font-medium ${convertResult.success ? 'text-[#4ade80]' : 'text-[#f87171]'}`}>
                  {convertResult.message}
                </h4>
                {convertResult.success && (
                  <p className="text-sm text-[#71717a] mt-1">
                    成功转换 {convertResult.convertedCount} 个课程，现在可以导入到数据库
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {convertResult.success && (
                <button 
                  onClick={() => {
                    setConvertResult(null);
                    setActiveTab('converted');
                  }}
                  className="btn btn-primary text-sm"
                >
                  去导入
                </button>
              )}
              <button onClick={() => setConvertResult(null)} className="text-[#71717a] hover:text-white">
                <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {importResult && (
        <div className={`mb-6 p-4 rounded-xl border ${importResult.success ? 'bg-[rgba(34,197,94,0.1)] border-[rgba(34,197,94,0.2)]' : 'bg-[rgba(239,68,68,0.1)] border-[rgba(239,68,68,0.2)]'}`}>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {importResult.success && (
                <div className="p-2 rounded-lg bg-[rgba(34,197,94,0.15)]">
                  <svg style={{width: '20px', height: '20px'}} fill="none" stroke="#4ade80" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
              <div>
                <h4 className={`font-medium ${importResult.success ? 'text-[#4ade80]' : 'text-[#f87171]'}`}>
                  {importResult.message}
                </h4>
                {importResult.success && (
                  <p className="text-sm text-[#71717a] mt-1">
                    已导入 {importResult.imported_courses} 个课程，{importResult.imported_chapters} 个章节
                  </p>
                )}
                {importResult.errors.length > 0 && (
                  <div className="mt-2 text-sm text-[#a1a1aa]">
                    {importResult.errors.slice(0, 3).map((err, i) => (
                      <div key={i}>• {err}</div>
                    ))}
                    {importResult.errors.length > 3 && (
                      <div>...还有 {importResult.errors.length - 3} 个错误</div>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {importResult.success && (
                <button 
                  onClick={() => {
                    setImportResult(null);
                    setActiveTab('database');
                  }}
                  className="btn btn-primary text-sm"
                >
                  查看已导入
                </button>
              )}
              <button onClick={() => setImportResult(null)} className="text-[#71717a] hover:text-white">
                <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {quizResult && (
        <div className={`mb-6 p-4 rounded-xl border ${quizResult.success ? 'bg-[rgba(34,197,94,0.1)] border-[rgba(34,197,94,0.2)]' : 'bg-[rgba(59,130,246,0.1)] border-[rgba(59,130,246,0.2)]'}`}>
          <div className="flex items-start justify-between">
            <div>
              <h4 className={`font-medium ${quizResult.success ? 'text-[#4ade80]' : 'text-[#60a5fa]'}`}>
                {quizResult.message}
              </h4>
              <div className="mt-1 text-sm text-[#a1a1aa]">
                已处理 {quizResult.chapters_processed} 个章节
              </div>
            </div>
            <button onClick={() => setQuizResult(null)} className="text-[#71717a] hover:text-white">
              <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-6">
        <TabButton 
          active={activeTab === 'raw'} 
          onClick={() => setActiveTab('raw')}
          count={stats.raw}
        >
          原始课程
        </TabButton>
        <TabButton 
          active={activeTab === 'converted'} 
          onClick={() => setActiveTab('converted')}
          count={stats.converted}
        >
          已转换
        </TabButton>
        <TabButton 
          active={activeTab === 'database'} 
          onClick={() => setActiveTab('database')}
          count={stats.database}
        >
          已导入
        </TabButton>
      </div>

      {activeTab === 'raw' && (
        <div>
          <div className="flex justify-end mb-4">
            <button 
              onClick={handleConvert} 
              disabled={actionLoading === 'convert'} 
              className="btn btn-primary"
            >
              {actionLoading === 'convert' ? (
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
                  一键转换所有课程
                </>
              )}
            </button>
          </div>
          
          {rawCourses.length === 0 ? (
            <EmptyState 
              title="暂无原始课程" 
              description="raw_courses 目录下没有待转换的课程"
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {rawCourses.map(course => (
                <RawCourseCard 
                  key={course.id} 
                  course={course}
                  onConvert={handleConvertSingle}
                  loading={actionLoading}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'converted' && (
        <div>
          <div className="flex justify-end mb-4">
            <button 
              onClick={handleImport} 
              disabled={actionLoading === 'import'} 
              className="btn btn-primary"
            >
              {actionLoading === 'import' ? (
                <>
                  <svg style={{width: '14px', height: '14px'}} className="icon-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  导入中...
                </>
              ) : (
                <>
                  <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
一键导入所有课程
                </>
              )}
            </button>
          </div>
          
          {convertedCourses.length === 0 ? (
            <EmptyState 
              title="暂无转换后的课程" 
              description="courses 目录下没有课程，请先转换原始课程"
              action={
                <button onClick={handleConvert} disabled={actionLoading === 'convert'} className="btn btn-primary">
                  转换课程
                </button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {convertedCourses.map(course => (
                <CourseCard 
                  key={course.id} 
                  course={course} 
                  onGenerateQuiz={handleGenerateQuiz}
                  onImport={handleImportSingle}
                  actionLoading={actionLoading}
                  onManageWordcloud={(id, name) => setWordcloudModal({ courseId: id, courseName: name })}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'database' && (
        <div>
          {databaseCourses.length === 0 ? (
            <EmptyState 
              title="数据库中没有课程" 
              description="请先导入转换后的课程到数据库"
              action={
                <button onClick={handleImport} disabled={actionLoading === 'import'} className="btn btn-primary">
                  导入课程
                </button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {databaseCourses.map(course => (
                <DatabaseCourseCard 
                  key={course.id} 
                  course={course} 
                  onDelete={handleDeleteFromDb}
                  loading={actionLoading === `delete-${course.id}`}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
    {/* 词云管理弹窗 */}
    {wordcloudModal && (
      <WordcloudManager
        courseId={wordcloudModal.courseId}
        courseName={wordcloudModal.courseName}
        onClose={() => setWordcloudModal(null)}
      />
    )}
    </>
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

function StatCard({ label, value, icon, gradient, highlight, subtitle }: { 
  label: string; 
  value: string | number; 
  icon: string;
  gradient?: boolean;
  highlight?: boolean;
  subtitle?: string;
}) {
  const icons: Record<string, React.ReactNode> = {
    inbox: (
      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
      </svg>
    ),
    folder: (
      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
      </svg>
    ),
    database: (
      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
      </svg>
    ),
    clock: (
      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
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
      {subtitle && (
        <div className="text-[12px] text-[#52525b] mt-1">{subtitle}</div>
      )}
    </div>
  );
}

function TabButton({ children, active, onClick, count }: { 
  children: React.ReactNode; 
  active: boolean; 
  onClick: () => void;
  count?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
        active 
          ? 'bg-[rgba(139,92,246,0.15)] text-[#a78bfa]' 
          : 'text-[#71717a] hover:text-[#a1a1aa] hover:bg-[rgba(255,255,255,0.03)]'
      }`}
    >
      {children}
      {count !== undefined && count > 0 && (
        <span className={`px-1.5 py-0.5 rounded text-[12px] ${
          active ? 'bg-[rgba(139,92,246,0.3)]' : 'bg-[rgba(255,255,255,0.1)]'
        }`}>
          {count}
        </span>
      )}
    </button>
  );
}

function EmptyState({ title, description, action }: { 
  title: string; 
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="card p-12 text-center">
      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-[rgba(139,92,246,0.2)] to-[rgba(6,182,212,0.1)] flex items-center justify-center">
        <svg style={{width: '28px', height: '28px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} className="text-[#a78bfa]">
          <path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-[#fafafa] mb-2">{title}</h3>
      <p className="text-sm text-[#71717a] mb-6 max-w-xs mx-auto">{description}</p>
      {action}
    </div>
  );
}

function RawCourseCard({ course, onConvert, loading }: { 
  course: RawCourse; 
  onConvert: (courseId: string) => void;
  loading: string | null;
}) {
  return (
    <div className="card p-5 group">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-[rgba(245,158,11,0.1)]">
          <svg style={{width: '18px', height: '18px'}} fill="none" stroke="#fbbf24" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-[16px] font-medium text-[#fafafa] truncate">{course.name}</h3>
          <div className="flex items-center gap-3 mt-1 text-sm text-[#71717a]">
            <span>{course.file_count} 文件</span>
            {course.has_content && (
              <span className="tag tag-warning text-[12px]">含 Markdown</span>
            )}
          </div>
        </div>
      </div>
      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity mt-4 pt-4 border-t border-[rgba(255,255,255,0.06)]">
        <button 
          onClick={() => onConvert(course.id)}
          disabled={loading === `convert-${course.id}`}
          className="btn btn-primary flex-1 text-sm"
        >
          {loading === `convert-${course.id}` ? '转换中...' : '转换'}
        </button>
      </div>
    </div>
  );
}

function CourseCard({ course, onGenerateQuiz, onImport, onManageWordcloud, actionLoading }: { 
  course: Course; 
  onGenerateQuiz: (courseId: string) => void;
  onImport: (courseId: string) => void;
  onManageWordcloud: (courseId: string, courseName: string) => void;
  actionLoading: string | null;
}) {
  const score = course.quality_score;
  const hasScore = score !== undefined && score !== null;
  const scoreLevel = hasScore ? (score! >= 80 ? 'high' : score! >= 60 ? 'medium' : 'low') : 'none';
  
  const scoreColors = {
    high: { text: 'text-[#4ade80]', bg: 'bg-[rgba(34,197,94,0.1)]' },
    medium: { text: 'text-[#fbbf24]', bg: 'bg-[rgba(245,158,11,0.1)]' },
    low: { text: 'text-[#f87171]', bg: 'bg-[rgba(239,68,68,0.1)]' },
    none: { text: 'text-[#71717a]', bg: 'bg-[rgba(255,255,255,0.03)]' },
  };

  return (
    <div className="card card-glow p-5 group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center px-2.5 py-1 rounded text-[12px] font-medium bg-[rgba(139,92,246,0.1)] text-[#a78bfa] border border-[rgba(139,92,246,0.2)]">
              {course.code}
            </span>
          </div>
          <h3 className="text-[17px] font-medium text-[#fafafa] truncate">{course.title}</h3>
        </div>
        
        <div className={`flex flex-col items-end px-3 py-1.5 rounded-lg ${scoreColors[scoreLevel].bg}`}>
          <span className={`text-xl font-bold ${scoreColors[scoreLevel].text}`}>
            {hasScore ? score : '-'}
          </span>
          <span className="text-[9px] text-[#71717a] uppercase tracking-wider">质量分</span>
        </div>
      </div>

      <p className="text-sm text-[#71717a] line-clamp-2 mb-4 min-h-[32px]">
        {course.description || '暂无描述'}
      </p>

      <div className="flex items-center gap-4 text-sm text-[#71717a] mb-4 pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <span className="flex items-center gap-1.5">
          <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {course.chapters?.length || 0} 章节
        </span>
      </div>

      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button 
          onClick={() => onImport(course.id)}
          disabled={actionLoading === `import-${course.id}`}
          className="btn btn-primary flex-1 text-sm"
        >
          {actionLoading === `import-${course.id}` ? '导入中...' : '导入'}
        </button>
        <button 
          onClick={() => onGenerateQuiz(course.id)}
          disabled={actionLoading === `quiz-${course.id}`}
          className="btn btn-ghost flex-1 text-sm text-[#60a5fa]"
        >
          {actionLoading === `quiz-${course.id}` ? '生成中...' : '生成题目'}
        </button>
        <button 
          onClick={() => onManageWordcloud(course.id, course.title)}
          className="btn btn-ghost flex-1 text-sm text-[#a78bfa]"
        >
          词云
        </button>
        <a 
          href={`/optimization?course=${course.id}`} 
          className="btn btn-secondary flex-1 text-sm"
        >
          RAG 优化
        </a>
      </div>
    </div>
  );
}

function DatabaseCourseCard({ course, onDelete, loading }: { 
  course: DatabaseCourse; 
  onDelete: (id: string) => void;
  loading: boolean;
}) {
  return (
    <div className="card p-5 group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center px-2.5 py-1 rounded text-[12px] font-medium bg-[rgba(34,197,94,0.1)] text-[#4ade80] border border-[rgba(34,197,94,0.2)]">
              {course.code}
            </span>
            {course.is_active ? (
              <span className="tag tag-success text-[12px]">启用</span>
            ) : (
              <span className="tag tag-error text-[12px]">禁用</span>
            )}
          </div>
          <h3 className="text-[17px] font-medium text-[#fafafa] truncate">{course.title}</h3>
        </div>
        
        <div className="p-2 rounded-lg bg-[rgba(34,197,94,0.1)]">
          <svg style={{width: '18px', height: '18px'}} fill="none" stroke="#4ade80" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
        </div>
      </div>

      <p className="text-sm text-[#71717a] line-clamp-2 mb-4 min-h-[32px]">
        {course.description || '暂无描述'}
      </p>

      <div className="flex items-center gap-4 text-sm text-[#71717a] mb-4 pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <span className="flex items-center gap-1.5">
          <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {course.chapter_count} 章节
        </span>
        <span className="tag tag-info text-[12px]">{course.course_type}</span>
      </div>

      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <a 
          href={`/learning/${course.id}`} 
          className="btn btn-secondary flex-1 text-sm"
        >
          查看课程
        </a>
        <button 
          onClick={() => onDelete(course.id)} 
          disabled={loading}
          className="btn btn-ghost flex-1 text-sm text-[#f87171]"
        >
          {loading ? '删除中...' : '删除'}
        </button>
      </div>
    </div>
  );
}
