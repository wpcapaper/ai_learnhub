/**
 * RAG 召回测试页面
 * 
 * 提供可视化界面测试RAG检索效果：
 * - 输入查询测试召回
 * - 查看召回结果
 * - 评估召回质量
 */

'use client';

import { useState, useEffect } from 'react';
import { adminApi, RAGTestResult, Course } from '@/lib/api';

export default function RAGTestPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>('');
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RAGTestResult | null>(null);
  const [indexStatus, setIndexStatus] = useState<{ chunk_count: number } | null>(null);

  // 加载课程列表
  useEffect(() => {
    loadCourses();
  }, []);

  // 当选择课程时，获取索引状态
  useEffect(() => {
    if (selectedCourse) {
      loadIndexStatus(selectedCourse);
    }
  }, [selectedCourse]);

  const loadCourses = async () => {
    const response = await adminApi.getCourses();
    if (response.success && response.data) {
      setCourses(response.data);
      if (response.data.length > 0) {
        setSelectedCourse(response.data[0].id);
      }
    }
  };

  const loadIndexStatus = async (courseId: string) => {
    const response = await adminApi.getIndexStatus(courseId);
    if (response.success && response.data) {
      setIndexStatus(response.data);
    } else {
      setIndexStatus(null);
    }
  };

  const handleSearch = async () => {
    if (!query.trim() || !selectedCourse) return;

    setLoading(true);
    setResult(null);

    const response = await adminApi.testRetrieval(selectedCourse, query, topK);
    
    if (response.success && response.data) {
      setResult(response.data);
    } else {
      alert(`搜索失败: ${response.error}`);
    }
    
    setLoading(false);
  };

  const handleRebuildIndex = async () => {
    if (!selectedCourse) return;
    
    if (!confirm(`确定要重建课程 ${selectedCourse} 的索引吗？这可能需要一些时间。`)) {
      return;
    }

    setLoading(true);
    const response = await adminApi.rebuildIndex(selectedCourse);
    
    if (response.success) {
      alert('索引重建成功！');
      loadIndexStatus(selectedCourse);
    } else {
      alert(`重建失败: ${response.error}`);
    }
    
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold text-green-400 font-mono">
          &gt;_ RAG 召回测试
        </h1>
        <p className="text-gray-500 text-sm mt-1 font-mono">
          测试检索增强生成的召回效果
        </p>
      </div>

      {/* 控制面板 */}
      <div className="terminal">
        <div className="terminal-line text-cyan-400 mb-4">
          === 测试配置 ===
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* 课程选择 */}
          <div>
            <label className="block text-gray-400 text-sm mb-2">选择课程</label>
            <select
              value={selectedCourse}
              onChange={(e) => setSelectedCourse(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded font-mono"
            >
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.code} - {course.title}
                </option>
              ))}
            </select>
          </div>

          {/* Top K */}
          <div>
            <label className="block text-gray-400 text-sm mb-2">返回数量 (Top K)</label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded font-mono"
            >
              {[3, 5, 10, 15, 20].map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 索引状态 */}
        {indexStatus && (
          <div className="mb-4 p-3 border border-gray-700 rounded">
            <span className="text-gray-400">索引状态: </span>
            <span className="text-green-400">{indexStatus.chunk_count} 个文档块</span>
            <button
              onClick={handleRebuildIndex}
              className="ml-4 text-yellow-400 hover:text-yellow-300"
            >
              [重建索引]
            </button>
          </div>
        )}

        {/* 查询输入 */}
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="输入查询问题..."
            className="flex-1 bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded font-mono focus:border-cyan-500 focus:outline-none"
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-6 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 
                       text-black font-mono rounded transition-colors"
          >
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>
      </div>

      {/* 搜索结果 */}
      {result && (
        <div className="terminal">
          <div className="flex justify-between items-center mb-4">
            <div className="text-cyan-400">
              === 搜索结果 ({result.total}) ===
            </div>
            <div className="text-gray-500 text-sm">
              查询: &quot;{result.query}&quot;
            </div>
          </div>

          {result.results.length === 0 ? (
            <div className="terminal-line text-gray-500">
              没有找到相关内容
            </div>
          ) : (
            <div className="space-y-4">
              {result.results.map((item, index) => (
                <div key={item.chunk_id} className="border border-gray-700 rounded p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400">#{index + 1}</span>
                      <span className="text-gray-500 text-sm">{item.source}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-xs">
                        <span className="text-gray-500">相似度: </span>
                        <span className={
                          item.score >= 0.8 ? 'text-green-400' :
                          item.score >= 0.5 ? 'text-yellow-400' : 'text-red-400'
                        }>
                          {(item.score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* 相似度进度条 */}
                  <div className="progress-bar mb-2">
                    <div 
                      className="progress-fill"
                      style={{ width: `${item.score * 100}%` }}
                    />
                  </div>
                  
                  {/* 内容 */}
                  <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                    {item.text.length > 500 ? (
                      <>
                        {item.text.slice(0, 500)}
                        <span className="text-gray-500">... (已截断)</span>
                      </>
                    ) : (
                      item.text
                    )}
                  </div>

                  {/* 元数据 */}
                  {item.metadata && Object.keys(item.metadata).length > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      {Object.entries(item.metadata).slice(0, 3).map(([key, value]) => (
                        <span key={key} className="mr-4">
                          {key}: {String(value).slice(0, 30)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 使用提示 */}
      <div className="terminal">
        <div className="text-yellow-400 mb-2">=== 使用提示 ===</div>
        <ul className="text-gray-400 text-sm space-y-1">
          <li>• 选择要测试的课程，确保课程已建立索引</li>
          <li>• 输入自然语言问题，系统会返回相关文档片段</li>
          <li>• 相似度越高表示与查询越相关</li>
          <li>• 如果召回效果不佳，尝试调整分块策略</li>
          <li>• 可以使用 [RAG专家] 页面进行策略优化</li>
        </ul>
      </div>
    </div>
  );
}
