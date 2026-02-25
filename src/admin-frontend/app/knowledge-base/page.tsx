'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  adminApi, 
  RAGStatus, 
  ChapterKBConfig, 
  DocumentChunk, 
  Course
} from '@/lib/api';

type TabType = 'chunks' | 'config' | 'test';

// Toast 通知类型
interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

// 全局 Toast 状态
const toasts: Toast[] = [];
let setToastsFn: React.Dispatch<React.SetStateAction<Toast[]>> | null = null;

const showToast = (type: Toast['type'], message: string) => {
  const id = Date.now().toString();
  if (setToastsFn) {
    setToastsFn(prev => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToastsFn?.(prev => prev.filter(t => t.id !== id));
    }, 3000);
  }
};

// 章节扩展信息（包含索引状态）
interface ChapterWithId {
  title: string;
  file: string;
  sort_order: number;
  indexStatus?: string;
  chunkCount?: number;
  // 当前正在执行的任务信息
  currentTaskId?: string;
  taskStatus?: string;
}

interface CourseWithId {
  id: string;
  title: string;
  code: string;
  description: string;
  chapters: ChapterWithId[];
}

// 后端返回的待处理任务结构
interface PendingTask {
  task_id: string;
  temp_ref: string;
  chapter_file: string;
  status: string;
  error: string | null;
}

export default function KnowledgeBasePage() {
  const [ragStatus, setRAGStatus] = useState<RAGStatus | null>(null);
  const [courses, setCourses] = useState<CourseWithId[]>([]);
  const [selectedCourseCode, setSelectedCourseCode] = useState<string>('');
  const [selectedChapterIndex, setSelectedChapterIndex] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<TabType>('chunks');
  const [loading, setLoading] = useState(true);
  const [batchIndexing, setBatchIndexing] = useState(false);
  const [batchProgress, setBatchProgress] = useState<string>('');
  const [chunksRefreshKey, setChunksRefreshKey] = useState(0);
  // syncingCourse 和 syncProgress 已移除
  const [toasts, setToasts] = useState<Toast[]>([]);
  
  // 待处理任务状态：key 为 task_id，value 为任务详情
  const [pendingTasks, setPendingTasks] = useState<Map<string, PendingTask>>(new Map());
  // 使用 ref 存储任务列表，避免轮询函数依赖 state
  const pendingTasksRef = useRef<Map<string, PendingTask>>(new Map());
  // 轮询定时器引用
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  // 保存最新的 courses 用于回调
  const coursesRef = useRef<CourseWithId[]>([]);

  useEffect(() => {
    coursesRef.current = courses;
  }, [courses]);


  // 注册全局 toast 函数
  useEffect(() => {
    setToastsFn = setToasts;
    return () => { setToastsFn = null; };
  }, []);

  useEffect(() => {
    loadData();
  }, []);

  // 拉取指定课程的待处理任务
  const fetchPendingTasks = useCallback(async (courseCode: string) => {
    const res = await adminApi.getCoursePendingTasks(courseCode);
    if (res.success && res.data?.tasks) {
      const taskMap = new Map<string, PendingTask>();
      res.data.tasks.forEach(task => {
        taskMap.set(task.task_id, task);
      });
      pendingTasksRef.current = taskMap;
      setPendingTasks(taskMap);
      return res.data.tasks;
    }
    return [];
  }, []);

  const selectedCourse = courses.find(c => c.code === selectedCourseCode);
  const selectedChapter = selectedCourse?.chapters?.[selectedChapterIndex];
  const selectedChapterOrder = selectedChapter?.sort_order ?? 0;

  // 轮询所有待处理任务的状态
  const pollPendingTasks = useCallback(async () => {
    const currentTasks = pendingTasksRef.current;
    if (currentTasks.size === 0) return;

    const taskIds = Array.from(currentTasks.keys());
    const completedFiles: string[] = [];
    const newTaskMap = new Map(currentTasks);

    for (const taskId of taskIds) {
      const res = await adminApi.getTaskStatus(taskId);
      if (res.success && res.data) {
        const taskData = res.data;
        const task = newTaskMap.get(taskId);
        if (task) {
          if (taskData.status === 'finished' || taskData.status === 'failed') {
            newTaskMap.delete(taskId);
            completedFiles.push(task.chapter_file);
          } else {
            newTaskMap.set(taskId, { ...task, status: taskData.status });
          }
        }
      }
    }

    // 只在有变化时更新
    if (newTaskMap.size !== currentTasks.size || completedFiles.length > 0) {
      pendingTasksRef.current = newTaskMap;
      setPendingTasks(new Map(newTaskMap));
      
      // 批量更新章节状态
      if (completedFiles.length > 0) {
        setCourses(prev => prev.map(c => {
          if (c.code !== selectedCourseCode) return c;
          return {
            ...c,
            chapters: c.chapters.map(ch => {
              if (completedFiles.includes(ch.file)) {
                return {
                  ...ch,
                  indexStatus: 'indexed',
                  currentTaskId: undefined,
                  taskStatus: undefined
                };
              }
              return ch;
            })
          };
        }));
      }
      
      // 如果所有任务都完成了，刷新并停止轮询
      if (newTaskMap.size === 0) {
        setBatchIndexing(false);
        setBatchProgress('');
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        loadChapterIndexStatus(selectedCourseCode);
        if (selectedChapterOrder > 0) {
          setChunksRefreshKey(prev => prev + 1);
        }
      }
    }
  }, [selectedCourseCode, selectedChapterOrder]);

  // 页面加载时检查是否有待处理任务
  useEffect(() => {
    if (selectedCourseCode) {
      fetchPendingTasks(selectedCourseCode);
    }
  }, [selectedCourseCode, fetchPendingTasks]);

  // 当有待处理任务时启动轮询
  useEffect(() => {
    if (pendingTasks.size > 0 && !pollingRef.current) {
      pollingRef.current = setInterval(pollPendingTasks, 2000);
    } else if (pendingTasks.size === 0 && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [pendingTasks.size, pollPendingTasks]);

  const loadData = async () => {
    setLoading(true);
    
    const [statusRes, coursesRes] = await Promise.all([
      adminApi.getRAGStatus(),
      adminApi.getMarkdownCourses(),
    ]);
    
    if (statusRes.success && statusRes.data) {
      setRAGStatus(statusRes.data);
    }
    
    if (coursesRes.success && coursesRes.data) {
      const mergedCourses: CourseWithId[] = coursesRes.data.map(course => ({
        id: course.id,
        title: course.title,
        code: course.code,
        description: course.description,
        chapters: (course.chapters || []).map(ch => ({
          title: ch.title,
          file: ch.file,
          sort_order: ch.sort_order,
          indexStatus: 'not_indexed',
          chunkCount: 0
        })),
      }));
      
      setCourses(mergedCourses);
      if (mergedCourses.length > 0) {
        setSelectedCourseCode(mergedCourses[0].code);
      }
    }
    
    setLoading(false);
  };

  const loadChapterIndexStatus = useCallback(async (courseCode: string) => {
    const course = coursesRef.current.find(c => c.code === courseCode);
    if (!course) return;
    
    const statuses = await Promise.all(
      course.chapters.map(async (ch) => {
        try {
          const res = await adminApi.getChapterKBConfigByRef(courseCode, ch.sort_order);
          if (res.success && res.data) {
            return {
              file: ch.file,
              indexStatus: String(res.data.stats?.index_status || 'not_indexed'),
              chunkCount: Number(res.data.stats?.chunk_count || 0)
            };
          }
        } catch {}
        return { file: ch.file, indexStatus: 'not_indexed', chunkCount: 0 };
      })
    );
    
    const statusMap = new Map(statuses.map(s => [s.file, s]));
    
    setCourses(prev => prev.map(c => {
      if (c.code !== courseCode) return c;
      return {
        ...c,
        chapters: c.chapters.map(ch => {
          const status = statusMap.get(ch.file);
          return status ? { ...ch, ...status } : ch;
        })
      };
    }));
  }, []);

  useEffect(() => {
    if (selectedCourseCode && courses.length > 0) {
      loadChapterIndexStatus(selectedCourseCode);
    }
  }, [selectedCourseCode, courses.length]);

  const handleBatchIndex = async () => {
    if (!selectedCourse || batchIndexing) return;
    
    setBatchIndexing(true);
    setBatchProgress('正在加入队列...');
    
    // 使用 code（课程代码/目录名）
    const courseCode = selectedCourse.code;
    
    const res = await adminApi.reindexCourse(courseCode, true);
    
    if (res.success && res.data) {
      setBatchProgress(`已加入队列，正在处理...`);
      
      const tasks = await fetchPendingTasks(courseCode);
      
      // 更新章节状态为处理中
      setCourses(prev => prev.map(c => {
        if (c.code !== selectedCourse.code) return c;
        return {
          ...c,
          chapters: c.chapters.map(ch => {
            const matchingTask = tasks.find((t: PendingTask) => t.chapter_file === ch.file);
            if (matchingTask) {
              return {
                ...ch,
                indexStatus: 'pending',
                currentTaskId: matchingTask.task_id,
                taskStatus: matchingTask.status
              };
            }
            return ch;
          })
        };
      }));
    } else {
      setBatchProgress(`加入队列失败: ${res.error}`);
      setBatchIndexing(false);
    }
  };

  // syncCourseToOnline 功能已移除

  const getIndexedCount = () => {
    if (!selectedCourse) return { indexed: 0, total: 0 };
    const indexed = selectedCourse.chapters.filter(ch => 
      ch.indexStatus === 'indexed' || ch.indexStatus === 'indexing'
    ).length;
    return { indexed, total: selectedCourse.chapters.length };
  };

  const StatusIndicator = () => (
    <div className="flex items-center gap-4 mb-6 p-4 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)]">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          loading ? 'bg-gray-400' : 
          ragStatus?.embedding?.available ? 'bg-green-400 animate-pulse' : 'bg-red-400'
        }`} />
        <span className="text-sm text-gray-400">Embedding:</span>
        {loading && !ragStatus ? (
          <div className="w-24 h-4 bg-gray-700 rounded animate-pulse" />
        ) : (
          <span className={`text-sm font-medium ${ragStatus?.embedding?.available ? 'text-green-400' : 'text-red-400'}`}>
            {ragStatus?.embedding?.available ? `${ragStatus.embedding.provider} / ${ragStatus.embedding.model}` : '不可用'}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          loading ? 'bg-gray-400' :
          ragStatus?.rerank?.available ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'
        }`} />
        <span className="text-sm text-gray-400">Rerank:</span>
        {loading && !ragStatus ? (
          <div className="w-16 h-4 bg-gray-700 rounded animate-pulse" />
        ) : (
          <span className={`text-sm font-medium ${ragStatus?.rerank?.available ? 'text-green-400' : 'text-yellow-400'}`}>
            {ragStatus?.rerank?.available ? `${ragStatus.rerank.provider}` : '未配置'}
          </span>
        )}
      </div>
    </div>
  );

  if (!loading && ragStatus && !ragStatus.ready) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-white mb-4">知识库管理</h1>
        <div className="card p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-red-500/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Embedding 服务不可用</h2>
          <p className="text-gray-400 mb-4">{ragStatus.embedding.message}</p>
          <p className="text-sm text-gray-500">请检查 .env 文件中的 RAG_EMBEDDING_* 配置</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Toast 通知容器 */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map(toast => (
          <div 
            key={toast.id}
            className={`px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 animate-slide-in ${
              toast.type === 'success' ? 'bg-green-500/90 text-white' :
              toast.type === 'error' ? 'bg-red-500/90 text-white' :
              'bg-blue-500/90 text-white'
            }`}
          >
            {toast.type === 'success' && <span>✓</span>}
            {toast.type === 'error' && <span>✕</span>}
            {toast.type === 'info' && <span>ℹ</span>}
            <span>{toast.message}</span>
          </div>
        ))}
      </div>

      <div className="mb-8">
        <div className="flex items-center gap-2 text-[13px] text-[#71717a] mb-2">
          <span>知识库</span>
          <svg style={{width: '12px', height: '12px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-[#a1a1aa]">章节管理</span>
        </div>
        <h1 className="text-2xl font-semibold text-[#fafafa]">知识库管理</h1>
      </div>

      <StatusIndicator />

      {/* 课程选择区域 */}
      <div className="card p-4 mb-6">
        {loading && courses.length === 0 ? (
          // 骨架屏
          <div className="flex gap-4 items-end animate-pulse">
            <div className="flex-1">
              <div className="w-16 h-4 bg-gray-700 rounded mb-2" />
              <div className="w-full h-10 bg-gray-700 rounded-lg" />
            </div>
            <div className="flex-1">
              <div className="w-16 h-4 bg-gray-700 rounded mb-2" />
              <div className="w-full h-10 bg-gray-700 rounded-lg" />
            </div>
            <div className="w-32 h-10 bg-gray-700 rounded-lg" />
          </div>
        ) : (
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm text-gray-400 mb-2">选择课程</label>
              <select
                value={selectedCourseCode}
                onChange={(e) => {
                  setSelectedCourseCode(e.target.value);
                  setSelectedChapterIndex(0);
                }}
                className="w-full bg-[#1e1e3f] border border-[rgba(99,102,241,0.2)] text-white px-3 py-2 rounded-lg"
              >
                {courses.map((course) => (
                  <option key={course.code} value={course.code}>
                    {course.title}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {selectedCourse && (
        <div className="mb-4 p-3 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)]">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-400">
              已索引: <span className="text-cyan-400 font-medium">{getIndexedCount().indexed}</span> / {getIndexedCount().total} 章节
            </div>
            <div className="flex items-center gap-2">
              {batchIndexing && (
                <>
                  <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm text-purple-400">{batchProgress}</span>
                </>
              )}
              <button
                onClick={handleBatchIndex}
                disabled={batchIndexing || !ragStatus?.ready}
                className="btn btn-primary text-sm"
              >
                {batchIndexing ? '索引中...' : '一键索引全部章节'}
              </button>
            </div>
          </div>
          
          {pendingTasks.size > 0 && (
            <div className="mt-3 pt-3 border-t border-[rgba(255,255,255,0.05)]">
              <div className="text-xs text-purple-300 mb-2">正在处理的章节：</div>
              <div className="space-y-1">
                {Array.from(pendingTasks.values()).map(task => (
                  <div key={task.task_id} className="flex items-center gap-2 text-xs">
                    <div className={`w-2 h-2 rounded-full ${
                      task.status === 'started' ? 'bg-green-400 animate-pulse' :
                      task.status === 'queued' ? 'bg-yellow-400' :
                      'bg-gray-400'
                    }`} />
                    <span className="text-gray-300">{task.chapter_file}</span>
                    <span className={`text-xs ${
                      task.status === 'started' ? 'text-green-400' :
                      task.status === 'queued' ? 'text-yellow-400' :
                      'text-gray-500'
                    }`}>
                      {task.status === 'started' ? '处理中' : task.status === 'queued' ? '排队中' : task.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-4 mb-6">
        <div className="flex-1">
          <label className="block text-sm text-gray-400 mb-2">选择章节</label>
          <select
            value={selectedChapterIndex}
            onChange={(e) => setSelectedChapterIndex(Number(e.target.value))}
            className="w-full bg-[#1e1e3f] border border-[rgba(99,102,241,0.2)] text-white px-3 py-2 rounded-lg"
            disabled={!selectedCourse?.chapters?.length}
          >
            {selectedCourse?.chapters?.map((chapter, idx) => (
              <option key={idx} value={idx}>
                {chapter.title} {chapter.indexStatus === 'indexed' ? `✓ (${chapter.chunkCount}块)` : chapter.indexStatus === 'indexing' || chapter.indexStatus === 'pending' ? '⏳' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {[
          { key: 'chunks', label: '文档块' },
          { key: 'config', label: '配置' },
          { key: 'test', label: '召回测试' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as TabType)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.key
                ? 'bg-[rgba(139,92,246,0.15)] text-[#a78bfa] border border-[rgba(139,92,246,0.3)]'
                : 'text-gray-400 hover:text-gray-300 hover:bg-[rgba(255,255,255,0.03)]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {selectedChapter ? (
        <>
          {activeTab === 'chunks' && selectedCourse && selectedChapter && (
            <ChunksTab
              courseCode={selectedCourse.code}
              sourceFile={selectedChapter.file}
              chapterOrder={selectedChapterOrder}
              refreshKey={chunksRefreshKey}
              onReindexTriggered={() => {
                fetchPendingTasks(selectedCourse.code);
              }}
            />
          )}
          {activeTab === 'config' && selectedCourse && selectedChapter && (
            <ConfigTab courseCode={selectedCourse.code} chapterOrder={selectedChapterOrder} />
          )}
          {activeTab === 'test' && selectedCourse && selectedChapter && (
            <TestTab courseCode={selectedCourse.code} sourceFile={selectedChapter.file} chapterOrder={selectedChapterOrder} />
          )}
        </>
      ) : (
        <div className="card p-8 text-center text-gray-500">
          请选择一个章节
        </div>
      )}
    </div>
  );
}

function ChunksTab({
  courseCode,
  sourceFile,
  chapterOrder,
  refreshKey,
  onReindexTriggered,
}: {
  courseCode: string;
  sourceFile: string;
  chapterOrder: number;
  refreshKey: number;
  onReindexTriggered?: (taskId: string) => void;
}) {
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChunk, setSelectedChunk] = useState<DocumentChunk | null>(null);
  const [chunkDetailLoading, setChunkDetailLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [reindexTaskId, setReindexTaskId] = useState<string | null>(null);
  const prevKeyRef = useRef<string | null>(null);
  const reindexPollingRef = useRef<NodeJS.Timeout | null>(null);

  const loadChunks = useCallback(async (resetPage = false) => {
    if (!courseCode || chapterOrder <= 0) return;
    
    if (resetPage) {
      setPage(1);
      setSearchQuery('');
      setSelectedChunk(null);
      setChunks([]);
      setTotal(0);
    }
    
    setLoading(true);
    
    const res = await adminApi.getChapterChunksByRef(courseCode, chapterOrder, {
      page: resetPage ? 1 : page,
      page_size: 10,
      search: searchQuery || undefined,
    });
    
    if (res.success && res.data) {
      setChunks(res.data.chunks);
      setTotal(res.data.total);
    }
    setLoading(false);
  }, [courseCode, chapterOrder, page, searchQuery]);

  useEffect(() => {
    const currentKey = `${courseCode}/${chapterOrder}`;
    if (currentKey !== prevKeyRef.current) {
      prevKeyRef.current = currentKey;
      loadChunks(true);
    }
  }, [courseCode, chapterOrder, loadChunks]);

  useEffect(() => {
    if (!refreshKey) return;
    setPage(1);
    setSearchQuery('');
    setSelectedChunk(null);
    setChunks([]);
    setTotal(0);
    loadChunks(true);
  }, [refreshKey, loadChunks]);

  // 监听 page 变化，仅加载（不重置）
  useEffect(() => {
    if (prevKeyRef.current) {
      loadChunks(false);
    }
  }, [page]);

  const pollReindexTask = useCallback(async (taskId: string) => {
    const res = await adminApi.getTaskStatus(taskId);
    if (res.success && res.data) {
      const status = res.data.status;
      if (status === 'finished') {
        setReindexing(false);
        setReindexTaskId(null);
        if (reindexPollingRef.current) {
          clearInterval(reindexPollingRef.current);
          reindexPollingRef.current = null;
        }
        loadChunks(true);
        return true;
      } else if (status === 'failed') {
        setReindexing(false);
        setReindexTaskId(null);
        if (reindexPollingRef.current) {
          clearInterval(reindexPollingRef.current);
          reindexPollingRef.current = null;
        }
        return true;
      }
    }
    return false;
  }, [loadChunks]);

  useEffect(() => {
    return () => {
      if (reindexPollingRef.current) {
        clearInterval(reindexPollingRef.current);
      }
    };
  }, []);

  const handleSearch = () => {
    setPage(1);
    loadChunks(true);
  };

  const handleReindex = async () => {
    if (!courseCode || chapterOrder <= 0 || reindexing) return;
    
    setReindexing(true);
    
    const res = await adminApi.reindexChapterByRef(courseCode, chapterOrder);
    
    if (res.success && res.data?.task_id) {
      const taskId = res.data.task_id;
      setReindexTaskId(taskId);
      onReindexTriggered?.(taskId);
      reindexPollingRef.current = setInterval(() => pollReindexTask(taskId), 2000);
    } else {
      setReindexing(false);
    }
  };

  const handleChunkClick = async (chunk: DocumentChunk) => {
    if (!courseCode) return;
    setChunkDetailLoading(true);
    const res = await adminApi.getChunkDetail(chunk.id, courseCode);
    if (res.success && res.data) {
      setSelectedChunk(res.data);
    } else {
      setSelectedChunk(chunk);
    }
    setChunkDetailLoading(false);
  };

  // syncChunksToDb 功能已移除

  // Token 级别配置
  const TOKEN_LEVELS = {
    normal: { color: 'text-green-400', bg: '', label: '正常' },
    warning: { color: 'text-yellow-400', bg: '', label: '偏大' },
    large: { color: 'text-orange-400', bg: 'border-orange-500/30', label: '较大' },
    oversized: { color: 'text-red-400', bg: 'border-red-500/30', label: '过大' },
  };

  // 统计各状态的 chunk 数量
  const getTokenStats = () => {
    const stats = { normal: 0, warning: 0, large: 0, oversized: 0 };
    chunks.forEach(chunk => {
      const level = (chunk as any).token_level || 'normal';
      if (stats.hasOwnProperty(level)) {
        stats[level as keyof typeof stats]++;
      }
    });
    return stats;
  };

  if (!sourceFile) return null;

  const tokenStats = getTokenStats();

  return (
    <div className="space-y-4">

      <div className="flex gap-4">
        <div className="flex-1 flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="搜索文档块内容..."
            className="flex-1 bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-4 py-2 rounded-lg focus:border-[rgba(139,92,246,0.5)] outline-none"
          />
          <button onClick={handleSearch} className="btn btn-secondary">搜索</button>
        </div>
        <button onClick={handleReindex} disabled={reindexing} className="btn btn-primary">
          {reindexing ? (
            <span className="flex items-center gap-2">
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              索引中...
            </span>
          ) : '重建索引'}
        </button>
      </div>

      {reindexing && (
        <div className="flex items-center gap-2 text-sm text-purple-400 p-2 rounded bg-purple-500/10">
          <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
          正在重建索引，请稍候...
        </div>
      )}

      {/* Token 大小分布统计 */}
      {chunks.length > 0 && (
        <div className="flex items-center gap-4 text-xs">
          <span className="text-gray-400">Token 分布:</span>
          <span className="text-green-400">正常(&lt;512): {tokenStats.normal}</span>
          <span className="text-yellow-400">偏大(512-1K): {tokenStats.warning}</span>
          <span className="text-orange-400">较大(1K-2K): {tokenStats.large}</span>
          <span className="text-red-400">过大(&gt;2K): {tokenStats.oversized}</span>
        </div>
      )}

      {loading ? (
        <div className="text-center text-gray-500 py-8">加载中...</div>
      ) : chunks.length === 0 ? (
        <div className="card p-8 text-center text-gray-500">
          暂无文档块，请先建立索引
        </div>
      ) : (
        <div className="space-y-3">
          {chunks.map((chunk, idx) => {
            const tokenLevel = (chunk as any).token_level || 'normal';
            const estimatedTokens = (chunk as any).estimated_tokens || 0;
            const levelConfig = TOKEN_LEVELS[tokenLevel as keyof typeof TOKEN_LEVELS];
            return (
              <div 
                key={chunk.id} 
                className={`card p-4 group cursor-pointer hover:border-[rgba(139,92,246,0.3)] transition-colors ${levelConfig.bg}`}
                onClick={() => handleChunkClick(chunk)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-400 text-sm">#{(page - 1) * 10 + idx + 1}</span>
                    <span className="text-xs text-gray-500">{chunk.source_file || '未知来源'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`tag ${chunk.content_type === 'summary' ? 'tag-warning' : 'tag-info'} text-xs`}>
                      {chunk.content_type === 'summary' ? '代码摘要' : chunk.content_type === 'code' ? '代码' : chunk.content_type === 'code_block' ? '代码块' : '文本'}
                    </span>
                    <span className={`text-xs ${levelConfig.color}`} title={`约 ${estimatedTokens} tokens`}>
                      ~{estimatedTokens}t
                    </span>
                    <span className="text-xs text-gray-500">{chunk.char_count}字符</span>
                    <span className={`tag ${chunk.is_active ? 'tag-success' : 'tag-error'} text-xs`}>
                      {chunk.is_active ? '启用' : '禁用'}
                    </span>
                  </div>
                </div>
                <div className="text-gray-300 text-sm line-clamp-2">
                  {chunk.content?.slice(0, 200) || '（内容需要加载）'}...
                </div>
                <div className="text-xs text-gray-500 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  点击查看全文
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 文档块详情弹窗 */}
      {selectedChunk && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedChunk(null)}
        >
          <div 
            className="bg-[#1e1e3f] rounded-xl max-w-3xl w-full max-h-[80vh] overflow-hidden border border-[rgba(139,92,246,0.2)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-[rgba(255,255,255,0.1)]">
              <div className="flex items-center gap-3">
                <span className="text-cyan-400 font-medium">文档块详情</span>
                <span className={`tag ${selectedChunk.content_type === 'summary' ? 'tag-warning' : 'tag-info'} text-xs`}>
                  {selectedChunk.content_type === 'summary' ? '代码摘要' : selectedChunk.content_type === 'code' ? '代码' : '文本'}
                </span>
              </div>
              <button 
                onClick={() => setSelectedChunk(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 border-b border-[rgba(255,255,255,0.05)]">
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>来源: {selectedChunk.source_file || '未知'}</span>
                <span>字符数: {selectedChunk.char_count}</span>
                <span>ID: {selectedChunk.id.slice(0, 8)}...</span>
              </div>
            </div>
            <div className="p-4 overflow-auto max-h-[60vh]">
              {chunkDetailLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <pre className="text-gray-300 text-sm whitespace-pre-wrap font-mono bg-[rgba(0,0,0,0.2)] p-4 rounded-lg">
                  {selectedChunk.content}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      {total > 10 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn btn-ghost text-sm disabled:opacity-50"
          >
            上一页
          </button>
          <span className="text-gray-400 text-sm py-2">
            第 {page} 页 / 共 {Math.ceil(total / 10)} 页
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page * 10 >= total}
            className="btn btn-ghost text-sm disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}

function ConfigTab({ courseCode, chapterOrder }: { courseCode: string; chapterOrder: number }) {
  const [config, setConfig] = useState<ChapterKBConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (courseCode && chapterOrder > 0) loadConfig();
  }, [courseCode, chapterOrder]);

  const loadConfig = async () => {
    if (!courseCode || chapterOrder <= 0) return;
    setLoading(true);
    
    const res = await adminApi.getChapterKBConfigByRef(courseCode, chapterOrder);
    
    if (res.success && res.data) {
      setConfig(res.data.config);
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!config || !courseCode || chapterOrder <= 0) return;
    setSaving(true);
    
    const res = await adminApi.updateChapterKBConfigByRef(courseCode, chapterOrder, config);
    
    if (res.success) {
      showToast('success', '配置已保存');
    } else {
      showToast('error', `保存失败: ${res.error}`);
    }
    setSaving(false);
  };

  if (loading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (!courseCode || chapterOrder <= 0) return null;

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h3 className="text-lg font-medium text-white mb-4">切分策略配置</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">策略类型</label>
            <select
              value={config?.chunking_strategy || 'semantic'}
              onChange={(e) => setConfig(c => c ? { ...c, chunking_strategy: e.target.value } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            >
              <option value="semantic">语义切分</option>
              <option value="fixed">固定大小</option>
              <option value="heading">按标题</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">最大块大小</label>
            <input
              type="number"
              value={config?.chunk_size || 1000}
              onChange={(e) => setConfig(c => c ? { ...c, chunk_size: Number(e.target.value) } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">重叠大小</label>
            <input
              type="number"
              value={config?.chunk_overlap || 200}
              onChange={(e) => setConfig(c => c ? { ...c, chunk_overlap: Number(e.target.value) } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">最小块大小</label>
            <input
              type="number"
              value={config?.min_chunk_size || 100}
              onChange={(e) => setConfig(c => c ? { ...c, min_chunk_size: Number(e.target.value) } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            />
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-medium text-white mb-4">代码块处理</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">处理策略</label>
            <select
              value={config?.code_block_strategy || 'hybrid'}
              onChange={(e) => setConfig(c => c ? { ...c, code_block_strategy: e.target.value } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            >
              <option value="preserve">保留原样</option>
              <option value="summarize">LLM摘要</option>
              <option value="hybrid">混合（推荐）</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">摘要阈值（字符）</label>
            <input
              type="number"
              value={config?.code_summary_threshold || 500}
              onChange={(e) => setConfig(c => c ? { ...c, code_summary_threshold: Number(e.target.value) } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            />
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-medium text-white mb-4">检索配置</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">检索模式</label>
            <select
              value={config?.retrieval_mode || 'vector'}
              onChange={(e) => setConfig(c => c ? { ...c, retrieval_mode: e.target.value } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            >
              <option value="vector">纯向量</option>
              <option value="hybrid">混合检索</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">默认 Top-K</label>
            <input
              type="number"
              value={config?.default_top_k || 5}
              onChange={(e) => setConfig(c => c ? { ...c, default_top_k: Number(e.target.value) } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">相似度阈值</label>
            <input
              type="number"
              step="0.1"
              value={config?.score_threshold || 0}
              onChange={(e) => setConfig(c => c ? { ...c, score_threshold: Number(e.target.value) } : null)}
              className="w-full bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-3 py-2 rounded-lg"
            />
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} disabled={saving} className="btn btn-primary">
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>
    </div>
  );
}

function TestTab({
  courseCode,
  sourceFile,
  chapterOrder,
}: {
  courseCode: string;
  sourceFile: string;
  chapterOrder: number;
}) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Array<{ chunk_id: string; content: string; score: number; source: string }>>([]);
  const [queryTime, setQueryTime] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedResult, setSelectedResult] = useState<{ chunk_id: string; content: string; score: number; source: string } | null>(null);
  // 召回参数
  const [topK, setTopK] = useState(5);
  const [scoreThreshold, setScoreThreshold] = useState(0);

  // 当前章节的文件名（用于判断召回结果是否来自其他章节）
  const currentChapterFile = sourceFile || '';

  const handleSearch = async () => {
    if (!query.trim()) return;
    if (!courseCode || chapterOrder <= 0) return;
    
    setLoading(true);
    
    const res = await adminApi.testChapterRetrievalByRef(courseCode, chapterOrder, query, { top_k: topK, score_threshold: scoreThreshold });
    
    if (res.success && res.data) {
      setResults(res.data.results);
      setQueryTime(res.data.query_time_ms);
    } else {
      showToast('error', `搜索失败: ${res.error}`);
    }
    setLoading(false);
  };

  // 规范化路径：统一分隔符、去除前缀等
  const normalizeSource = (source: string) => {
    return source
      .trim()
      .replace(/\\/g, '/')   // Windows路径分隔符统一为 /
      .replace(/\/+/g, '/')  // 合并重复斜杠
      .replace(/^\.\//, '')  // 去除 ./ 前缀
      .split('#')[0]          // 去除锚点
      .split('?')[0];         // 去除查询参数
  };

  // 判断召回结果是否来自其他章节
  const isFromOtherChapter = (source: string) => {
    return normalizeSource(source) !== normalizeSource(currentChapterFile);
  };

  if (!courseCode || !sourceFile) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-xs">
        <span className="text-gray-500">召回数据源:</span>
        <span className="px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
          课程分块 (ChromaDB)
        </span>
      </div>

      {/* 召回参数配置 */}
      <div className="card p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-400">Top-K:</label>
            <input
              type="number"
              min="1"
              max="20"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-16 bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-2 py-1 rounded text-sm"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-400">相似度阈值:</label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={scoreThreshold}
              onChange={(e) => setScoreThreshold(Number(e.target.value))}
              className="w-20 bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-2 py-1 rounded text-sm"
            />
          </div>
          <span className="text-xs text-gray-500">（0 表示不过滤）</span>
        </div>
      </div>
      
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="输入测试查询..."
          className="flex-1 bg-[#1e1e3f] border border-[rgba(255,255,255,0.1)] text-white px-4 py-3 rounded-lg focus:border-[rgba(139,92,246,0.5)] outline-none"
        />
        <button onClick={handleSearch} disabled={loading} className="btn btn-primary px-8">
          {loading ? '搜索中...' : '搜索'}
        </button>
      </div>

      {queryTime > 0 && (
        <div className="text-sm text-gray-400">
          找到 {results.length} 个结果，耗时 {queryTime.toFixed(2)}ms
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-4">
          {results.map((result, idx) => {
            const isOtherChapter = isFromOtherChapter(result.source);
            return (
              <div 
                key={result.chunk_id} 
                className={`card p-4 cursor-pointer hover:border-[rgba(139,92,246,0.3)] transition-colors ${
                  isOtherChapter ? 'border-amber-500/30 bg-amber-500/5' : ''
                }`}
                onClick={() => setSelectedResult(result)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-400">#{idx + 1}</span>
                    {isOtherChapter && (
                      <span className="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
                        跨章节
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-gray-500">{result.source}</span>
                    <span className={`text-sm font-medium ${
                      result.score >= 0.8 ? 'text-green-400' :
                      result.score >= 0.5 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {(result.score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="h-1 bg-gray-800 rounded-full mb-3">
                  <div 
                    className={`h-full rounded-full ${
                      result.score >= 0.8 ? 'bg-green-400' :
                      result.score >= 0.5 ? 'bg-yellow-400' : 'bg-red-400'
                    }`}
                    style={{ width: `${result.score * 100}%` }}
                  />
                </div>
                <div className="text-gray-300 text-sm line-clamp-3">
                  {result.content}
                </div>
                <div className="text-xs text-gray-500 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  点击查看全文
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 召回结果全文弹窗 */}
      {selectedResult && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedResult(null)}
        >
          <div 
            className="bg-[#1e1e3f] rounded-xl max-w-3xl w-full max-h-[80vh] overflow-hidden border border-[rgba(139,92,246,0.2)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-[rgba(255,255,255,0.1)]">
              <div className="flex items-center gap-3">
                <span className="text-cyan-400 font-medium">召回结果详情</span>
                {isFromOtherChapter(selectedResult.source) && (
                  <span className="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    跨章节召回
                  </span>
                )}
              </div>
              <button 
                onClick={() => setSelectedResult(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 border-b border-[rgba(255,255,255,0.05)]">
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>来源: {selectedResult.source}</span>
                <span>相似度: {(selectedResult.score * 100).toFixed(1)}%</span>
              </div>
            </div>
            <div className="p-4 overflow-auto max-h-[60vh]">
              <pre className="text-gray-300 text-sm whitespace-pre-wrap font-mono bg-[rgba(0,0,0,0.2)] p-4 rounded-lg">
                {selectedResult.content}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
