/**
 * 分块优化页面
 * 
 * 可视化展示不同分块策略的效果对比
 */

'use client';

import { useState, useEffect } from 'react';
import { adminApi, OptimizationReport, StrategyResult, Course } from '@/lib/api';

export default function OptimizationPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<OptimizationReport | null>(null);

  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    const response = await adminApi.getCourses();
    if (response.success && response.data) {
      setCourses(response.data);
      if (response.data.length > 0) {
        setSelectedCourse(response.data[0].id);
      }
    }
  };

  const runOptimization = async () => {
    if (!selectedCourse) return;

    setLoading(true);
    setReport(null);

    const response = await adminApi.runOptimization(selectedCourse);
    
    if (response.success && response.data) {
      setReport(response.data);
    } else {
      alert(`优化失败: ${response.error}`);
    }
    
    setLoading(false);
  };

  const loadReport = async () => {
    if (!selectedCourse) return;

    const response = await adminApi.getOptimizationReport(selectedCourse);
    if (response.success && response.data) {
      setReport(response.data);
    } else {
      alert('暂无优化报告，请先运行优化');
    }
  };

  // 计算图表最大值
  const getMaxRecall = () => {
    if (!report) return 1;
    return Math.max(...Object.values(report.strategy_results).map(r => r.avg_recall));
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold text-yellow-400 font-mono">
          &gt;_ 分块策略优化
        </h1>
        <p className="text-gray-500 text-sm mt-1 font-mono">
          测试不同分块策略，找出最佳RAG配置
        </p>
      </div>

      {/* 控制面板 */}
      <div className="terminal">
        <div className="terminal-line text-cyan-400 mb-4">
          === 优化配置 ===
        </div>

        <div className="flex gap-4 items-end">
          <div className="flex-1">
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
          <button
            onClick={runOptimization}
            disabled={loading || !selectedCourse}
            className="px-6 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:bg-gray-600 
                       text-black font-mono rounded transition-colors"
          >
            {loading ? '优化中...' : '运行优化'}
          </button>
          <button
            onClick={loadReport}
            disabled={!selectedCourse}
            className="px-6 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 
                       text-white font-mono rounded transition-colors"
          >
            加载报告
          </button>
        </div>
      </div>

      {/* 加载状态 */}
      {loading && (
        <div className="terminal">
          <div className="text-yellow-400">
            <span className="loading-dots">正在分析分块策略</span>
          </div>
          <div className="text-gray-500 text-sm mt-2">
            这可能需要几分钟时间，取决于课程内容大小...
          </div>
        </div>
      )}

      {/* 优化结果 */}
      {report && (
        <div className="space-y-6">
          {/* 总结 */}
          <div className="terminal">
            <div className="text-green-400 mb-2">=== 优化结果 ===</div>
            <div className="text-white">{report.summary}</div>
            <div className="mt-2">
              <span className="text-gray-400">推荐策略: </span>
              <span className="text-yellow-400 font-bold">{report.recommended_strategy}</span>
            </div>
          </div>

          {/* 策略对比图表 */}
          <div className="terminal">
            <div className="text-cyan-400 mb-4">=== 召回率对比 ===</div>
            
            <div className="space-y-4">
              {Object.entries(report.strategy_results)
                .sort((a, b) => b[1].avg_recall - a[1].avg_recall)
                .map(([name, result]) => {
                  const percentage = result.avg_recall * 100;
                  const isRecommended = name === report.recommended_strategy;
                  
                  return (
                    <div key={name} className={`p-3 border rounded ${isRecommended ? 'border-yellow-500' : 'border-gray-700'}`}>
                      <div className="flex justify-between items-center mb-2">
                        <div className="flex items-center gap-2">
                          {isRecommended && <span className="text-yellow-400">★</span>}
                          <span className={`font-mono ${isRecommended ? 'text-yellow-400' : 'text-white'}`}>
                            {name}
                          </span>
                        </div>
                        <span className={`font-mono ${isRecommended ? 'text-yellow-400' : 'text-green-400'}`}>
                          {percentage.toFixed(1)}%
                        </span>
                      </div>
                      
                      {/* 进度条 */}
                      <div className="progress-bar">
                        <div 
                          className={`progress-fill ${isRecommended ? 'bg-yellow-500' : 'bg-green-500'}`}
                          style={{ width: `${(result.avg_recall / getMaxRecall()) * 100}%` }}
                        />
                      </div>
                      
                      {/* 详细指标 */}
                      <div className="flex gap-6 mt-2 text-xs text-gray-500">
                        <span>分块数: {result.chunk_count}</span>
                        <span>平均大小: {result.avg_chunk_size.toFixed(0)} 字符</span>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* 推荐配置 */}
          <div className="terminal">
            <div className="text-cyan-400 mb-4">=== 推荐配置 ===</div>
            
            <div className="code-block">
              <pre className="text-gray-300 text-sm">
                {JSON.stringify(report.recommended_config, null, 2)}
              </pre>
            </div>
            
            <button
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(report.recommended_config, null, 2));
                alert('配置已复制到剪贴板');
              }}
              className="mt-2 text-cyan-400 hover:text-cyan-300"
            >
              [复制配置]
            </button>
          </div>

          {/* 详细数据表 */}
          <div className="terminal">
            <div className="text-cyan-400 mb-4">=== 详细数据 ===</div>
            
            <table className="terminal-table w-full">
              <thead>
                <tr>
                  <th>策略名称</th>
                  <th>召回率</th>
                  <th>分块数</th>
                  <th>平均大小</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.strategy_results)
                  .sort((a, b) => b[1].avg_recall - a[1].avg_recall)
                  .map(([name, result]) => (
                    <tr key={name} className={name === report.recommended_strategy ? 'text-yellow-400' : ''}>
                      <td>{name}</td>
                      <td>{(result.avg_recall * 100).toFixed(1)}%</td>
                      <td>{result.chunk_count}</td>
                      <td>{result.avg_chunk_size.toFixed(0)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 说明 */}
      {!report && !loading && (
        <div className="terminal">
          <div className="text-yellow-400 mb-2">=== 分块策略说明 ===</div>
          <div className="text-gray-400 text-sm space-y-2">
            <p>不同的分块策略会影响RAG系统的召回效果：</p>
            <ul className="list-disc list-inside space-y-1">
              <li><span className="text-white">semantic_small</span> - 小型语义块（100-500字符），召回细粒度高</li>
              <li><span className="text-white">semantic_medium</span> - 中型语义块（200-1000字符），平衡选择</li>
              <li><span className="text-white">semantic_large</span> - 大型语义块（500-2000字符），保留更多上下文</li>
              <li><span className="text-white">fixed_small</span> - 固定256字符，适合结构化内容</li>
              <li><span className="text-white">fixed_medium</span> - 固定512字符，通用选择</li>
              <li><span className="text-white">heading_based</span> - 按标题分割，保持章节完整</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
