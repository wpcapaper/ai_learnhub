/**
 * 首页 - 课程管理
 * 
 * 显示所有课程列表，支持转换操作和质量查看
 */

'use client';

import { useState, useEffect } from 'react';
import { adminApi, Course, QualityReport } from '@/lib/api';

export default function HomePage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [converting, setConverting] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null);
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);

  // 加载课程列表
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

  // 触发课程转换
  const handleConvert = async () => {
    setConverting(true);
    const response = await adminApi.convertCourses();
    setConverting(false);
    
    if (response.success) {
      alert('课程转换完成！');
      loadCourses();
    } else {
      alert(`转换失败: ${response.error}`);
    }
  };

  // 查看质量报告
  const handleViewQuality = async (courseId: string) => {
    setSelectedCourse(courseId);
    const response = await adminApi.getQualityReport(courseId);
    if (response.success && response.data) {
      setQualityReport(response.data);
    } else {
      setQualityReport(null);
    }
  };

  if (loading) {
    return (
      <div className="terminal">
        <div className="terminal-line terminal-dim">
          正在加载课程数据<span className="loading-dots"></span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 标题和操作 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-green-400 font-mono">
            &gt;_ 课程管理
          </h1>
          <p className="text-gray-500 text-sm mt-1 font-mono">
            管理课程转换和质量评估
          </p>
        </div>
        <button
          onClick={handleConvert}
          disabled={converting}
          className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 
                     text-black font-mono text-sm rounded transition-colors"
        >
          {converting ? '转换中...' : '[转换课程]'}
        </button>
      </div>

      {/* 课程列表 */}
      <div className="terminal">
        <div className="terminal-line text-cyan-400 mb-4">
          === 课程列表 ({courses.length}) ===
        </div>
        
        {courses.length === 0 ? (
          <div className="terminal-line terminal-dim">
            暂无课程数据。请先运行课程转换。
          </div>
        ) : (
          <table className="terminal-table w-full">
            <thead>
              <tr>
                <th>课程代码</th>
                <th>课程名称</th>
                <th>章节数</th>
                <th>质量评分</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((course) => (
                <tr key={course.id}>
                  <td className="text-cyan-400">{course.code}</td>
                  <td>{course.title}</td>
                  <td>{course.chapters?.length || 0}</td>
                  <td>
                    {course.quality_score !== undefined ? (
                      <span className={
                        course.quality_score >= 80 ? 'text-green-400' :
                        course.quality_score >= 60 ? 'text-yellow-400' : 'text-red-400'
                      }>
                        {course.quality_score}
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    <button
                      onClick={() => handleViewQuality(course.id)}
                      className="text-cyan-400 hover:text-cyan-300 mr-4"
                    >
                      [质量报告]
                    </button>
                    <a 
                      href={`/rag-test?course=${course.id}`}
                      className="text-green-400 hover:text-green-300"
                    >
                      [RAG测试]
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 质量报告弹窗 */}
      {qualityReport && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="terminal max-w-4xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <div className="text-cyan-400 text-lg">
                === 质量评估报告 ===
              </div>
              <button
                onClick={() => setQualityReport(null)}
                className="text-gray-400 hover:text-white"
              >
                [关闭]
              </button>
            </div>
            
            <div className="space-y-4">
              {/* 总体评分 */}
              <div className="metric-card">
                <div className="metric-label">总体评分</div>
                <div className={`metric-value ${
                  qualityReport.overall_score >= 80 ? 'text-green-400' :
                  qualityReport.overall_score >= 60 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {qualityReport.overall_score}/100
                </div>
              </div>

              {/* 问题统计 */}
              <div className="grid grid-cols-4 gap-4">
                <div className="metric-card">
                  <div className="metric-label">严重</div>
                  <div className="text-red-400 text-xl">{qualityReport.critical_issues}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">高</div>
                  <div className="text-orange-400 text-xl">{qualityReport.high_issues}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">中</div>
                  <div className="text-yellow-400 text-xl">{qualityReport.medium_issues}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">低</div>
                  <div className="text-gray-400 text-xl">{qualityReport.low_issues}</div>
                </div>
              </div>

              {/* 总结 */}
              <div className="terminal-line terminal-dim border-t border-gray-700 pt-4">
                {qualityReport.summary}
              </div>

              {/* 问题列表 */}
              {qualityReport.issues.length > 0 && (
                <div className="space-y-2">
                  <div className="text-cyan-400">发现问题：</div>
                  {qualityReport.issues.slice(0, 10).map((issue) => (
                    <div key={issue.issue_id} className="border-l-2 border-gray-600 pl-4 py-2">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          issue.severity === 'critical' ? 'bg-red-900 text-red-300' :
                          issue.severity === 'high' ? 'bg-orange-900 text-orange-300' :
                          issue.severity === 'medium' ? 'bg-yellow-900 text-yellow-300' :
                          'bg-gray-700 text-gray-300'
                        }`}>
                          {issue.severity.toUpperCase()}
                        </span>
                        <span className="text-gray-400 text-xs">{issue.issue_type}</span>
                      </div>
                      <div className="text-white mt-1">{issue.title}</div>
                      <div className="text-gray-500 text-sm mt-1">{issue.description}</div>
                      {issue.suggestion && (
                        <div className="text-cyan-400 text-sm mt-1">
                          建议: {issue.suggestion}
                        </div>
                      )}
                    </div>
                  ))}
                  {qualityReport.issues.length > 10 && (
                    <div className="text-gray-500 text-sm">
                      ... 还有 {qualityReport.issues.length - 10} 个问题
                    </div>
                  )}
                </div>
              )}

              {/* 建议 */}
              {qualityReport.recommendations.length > 0 && (
                <div className="space-y-2 border-t border-gray-700 pt-4">
                  <div className="text-yellow-400">整体建议：</div>
                  <ul className="list-disc list-inside text-gray-400">
                    {qualityReport.recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
