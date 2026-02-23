'use client';

import { useState, useEffect, useRef } from 'react';
import { adminApi, Course } from '@/lib/api';

interface TerminalLine {
  type: 'agent' | 'skill' | 'output' | 'success' | 'error' | 'progress' | 'result';
  content: string;
  skill?: string;
  data?: Record<string, unknown>;
}

export default function OptimizationPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>('');
  const [lines, setLines] = useState<TerminalLine[]>([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadCourses();
  }, []);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lines]);

  const loadCourses = async () => {
    const response = await adminApi.getCourses();
    if (response.success && response.data) {
      setCourses(response.data);
      const params = new URLSearchParams(window.location.search);
      const courseParam = params.get('course');
      if (courseParam && response.data.find(c => c.id === courseParam)) {
        setSelectedCourse(courseParam);
      } else if (response.data.length > 0) {
        setSelectedCourse(response.data[0].id);
      }
    }
  };

  const addLine = (line: TerminalLine) => {
    setLines(prev => [...prev, line]);
  };

  const runOptimization = async () => {
    if (!selectedCourse || running) return;

    setLines([]);
    setResult(null);
    setRunning(true);

    addLine({ type: 'agent', content: `[Agent] 开始 RAG 优化任务...` });
    addLine({ type: 'output', content: `[Agent] 目标课程: ${selectedCourse}` });

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_ADMIN_API_URL || 'http://localhost:8000'}/api/admin/rag/optimize/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ course_code: selectedCourse }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              handleEvent(event);
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (error) {
      addLine({ type: 'error', content: `[Error] ${error}` });
    } finally {
      setRunning(false);
    }
  };

  const handleEvent = (event: { type: string; content: string; skill?: string; data?: Record<string, unknown> }) => {
    switch (event.type) {
      case 'agent_start':
        addLine({ type: 'agent', content: `[Agent] ${event.content}` });
        break;
      case 'agent_thinking':
        addLine({ type: 'output', content: `       ${event.content}` });
        break;
      case 'skill_start':
        addLine({ type: 'skill', content: `[Skill] ${event.skill}: ${event.content}`, skill: event.skill });
        break;
      case 'skill_output':
        addLine({ type: 'output', content: `  → ${event.content}`, skill: event.skill, data: event.data });
        break;
      case 'skill_complete':
        addLine({ type: 'success', content: `  ✓ ${event.skill} 完成`, data: event.data });
        break;
      case 'progress':
        const progress = event.data as { current: number; total: number; percent: number };
        addLine({ type: 'progress', content: `[${progress.current}/${progress.total}] ${event.content}` });
        break;
      case 'agent_complete':
        addLine({ type: 'success', content: `\n[Agent] ===== 优化完成 =====` });
        if (event.data) {
          setResult(event.data);
          const data = event.data as { recommended_strategy?: string; summary?: string };
          if (data.recommended_strategy) {
            addLine({ type: 'result', content: `[推荐策略] ${data.recommended_strategy}` });
          }
          if (data.summary) {
            addLine({ type: 'output', content: data.summary });
          }
        }
        break;
      case 'agent_error':
        addLine({ type: 'error', content: `[Error] ${event.content}` });
        break;
      default:
        addLine({ type: 'output', content: event.content });
    }
  };

  const getLineColor = (type: TerminalLine['type']) => {
    switch (type) {
      case 'agent': return 'text-indigo-400';
      case 'skill': return 'text-cyan-400';
      case 'success': return 'text-green-400';
      case 'error': return 'text-red-400';
      case 'progress': return 'text-yellow-400';
      case 'result': return 'text-purple-400 font-bold';
      default: return 'text-gray-300';
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-white mb-0.5">RAG 优化工作台</h1>
          <p className="text-gray-500 text-sm">基于 Agent 的智能分块策略优化</p>
        </div>
        <div className="flex gap-2 items-center">
          <select
            value={selectedCourse}
            onChange={(e) => setSelectedCourse(e.target.value)}
            disabled={running}
            className="bg-[#1e1e3f] border border-[rgba(99,102,241,0.2)] text-white text-sm px-3 py-2 rounded-lg min-w-[180px]"
          >
            <option value="">选择课程</option>
            {courses.map((course) => (
              <option key={course.id} value={course.id}>
                {course.code} - {course.title}
              </option>
            ))}
          </select>
          <button onClick={runOptimization} disabled={running || !selectedCourse} className="btn btn-primary text-sm py-2 px-3">
            {running ? (
              <>
                <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="icon-spin">
                  <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                优化中...
              </>
            ) : (
              <>
                <svg style={{width: '14px', height: '14px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                启动优化
              </>
            )}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3">
          <div className="card p-0 overflow-hidden">
            <div className="terminal-header px-4 py-2 border-b border-[rgba(99,102,241,0.2)] bg-[#0d0d0d]">
              <div className="flex items-center gap-2">
                <span className="terminal-dot terminal-dot-red" />
                <span className="terminal-dot terminal-dot-yellow" />
                <span className="terminal-dot terminal-dot-green" />
                <span className="ml-3 text-gray-500 text-xs">Agent Console</span>
              </div>
            </div>
            <div ref={terminalRef} className="terminal min-h-[400px] rounded-none border-none">
              {lines.length === 0 ? (
                <div className="text-gray-600">
                  选择课程并点击"启动优化"开始...
                </div>
              ) : (
                lines.map((line, i) => (
                  <div key={i} className={`terminal-line ${getLineColor(line.type)}`}>
                    {line.content}
                  </div>
                ))
              )}
              {running && (
                <div className="terminal-line text-yellow-400">
                  <span className="loading-dots">处理中</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="card p-3">
            <h3 className="text-xs font-medium text-white mb-2">执行状态</h3>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">状态</span>
                <span className={running ? 'text-yellow-400' : result ? 'text-green-400' : 'text-gray-400'}>
                  {running ? '运行中' : result ? '已完成' : '待执行'}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">输出行数</span>
                <span className="text-white">{lines.length}</span>
              </div>
            </div>
          </div>

          {result && (
            <div className="card p-3">
              <h3 className="text-xs font-medium text-white mb-2">优化结果</h3>
              <div className="space-y-1.5 text-xs">
                {((result as { ranking?: { strategy: string; recall: number }[] }).ranking || []).slice(0, 5).map((r, i) => (
                  <div key={r.strategy} className="flex justify-between">
                    <span className={i === 0 ? 'text-yellow-400' : 'text-gray-400'}>
                      {i === 0 && '★ '}{r.strategy}
                    </span>
                    <span className="text-white">{(r.recall * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="card p-3">
            <h3 className="text-xs font-medium text-white mb-2">可用 Skills</h3>
            <div className="space-y-1 text-xs text-gray-500">
              <div>• analyze_content</div>
              <div>• test_chunking</div>
              <div>• generate_test_queries</div>
              <div>• evaluate_retrieval</div>
              <div>• compare_strategies</div>
              <div>• generate_summary</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
