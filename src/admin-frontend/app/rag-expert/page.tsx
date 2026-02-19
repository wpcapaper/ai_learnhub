/**
 * CLI风格 RAG 专家页面
 * 
 * 提供科技感的终端交互界面，用于：
 * - 自适应RAG策略调优
 * - 分块策略测试
 * - 召回效果评估
 */

'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { adminApi, OptimizationReport, StrategyResult } from '@/lib/api';

// 终端命令类型
interface TerminalLine {
  type: 'input' | 'output' | 'error' | 'success' | 'warning' | 'system';
  content: string;
  timestamp?: Date;
}

// 可用命令
const COMMANDS = {
  help: '显示帮助信息',
  status: '查看系统状态',
  courses: '列出可用课程',
  optimize: '运行分块优化测试',
  compare: '比较不同策略效果',
  config: '查看/修改RAG配置',
  models: '列出可用Embedding模型',
  clear: '清屏',
  exit: '返回首页',
};

export default function RAGExpertPage() {
  const [lines, setLines] = useState<TerminalLine[]>([
    { type: 'system', content: '╔════════════════════════════════════════════════════════════╗' },
    { type: 'system', content: '║   AILearn RAG Expert System v1.0.0                        ║' },
    { type: 'system', content: '║   自适应RAG策略优化工具                                   ║' },
    { type: 'system', content: '╚════════════════════════════════════════════════════════════╝' },
    { type: 'system', content: '' },
    { type: 'output', content: '系统初始化完成。输入 help 查看可用命令。' },
    { type: 'output', content: '' },
  ]);
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [currentCourse, setCurrentCourse] = useState<string | null>(null);
  const [optimizationResult, setOptimizationResult] = useState<OptimizationReport | null>(null);
  
  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lines]);

  // 添加行
  const addLine = useCallback((type: TerminalLine['type'], content: string) => {
    setLines(prev => [...prev, { type, content, timestamp: new Date() }]);
  }, []);

  // 处理命令
  const handleCommand = async (cmd: string) => {
    const parts = cmd.trim().split(/\s+/);
    const command = parts[0].toLowerCase();
    const args = parts.slice(1);

    addLine('input', `> ${cmd}`);

    switch (command) {
      case 'help':
        showHelp();
        break;
      
      case 'status':
        await showStatus();
        break;
      
      case 'courses':
        await listCourses();
        break;
      
      case 'optimize':
        await runOptimization(args);
        break;
      
      case 'compare':
        showComparison();
        break;
      
      case 'config':
        await showConfig(args);
        break;
      
      case 'models':
        await listModels();
        break;
      
      case 'clear':
        setLines([]);
        break;
      
      case 'exit':
        window.location.href = '/';
        break;
      
      case '':
        break;
      
      default:
        addLine('error', `未知命令: ${command}`);
        addLine('output', '输入 help 查看可用命令');
    }
  };

  // 显示帮助
  const showHelp = () => {
    addLine('output', '');
    addLine('success', '═══ 可用命令 ═══');
    Object.entries(COMMANDS).forEach(([cmd, desc]) => {
      addLine('output', `  ${cmd.padEnd(12)} - ${desc}`);
    });
    addLine('output', '');
    addLine('output', '提示: 使用 Tab 键自动补全命令');
    addLine('output', '');
  };

  // 显示系统状态
  const showStatus = async () => {
    addLine('output', '');
    addLine('success', '═══ 系统状态 ═══');
    
    try {
      // 获取可用模型
      const modelsRes = await adminApi.getEmbeddingModels();
      if (modelsRes.success && modelsRes.data) {
        addLine('output', `  Embedding模型: ${modelsRes.data.length} 个可用`);
      }
      
      // 当前选择
      if (currentCourse) {
        addLine('output', `  当前课程: ${currentCourse}`);
      } else {
        addLine('output', `  当前课程: 未选择`);
      }
      
      if (optimizationResult) {
        addLine('output', `  推荐策略: ${optimizationResult.recommended_strategy}`);
        addLine('output', `  状态: 优化完成 ✓`);
      }
    } catch (error) {
      addLine('error', '获取状态失败');
    }
    
    addLine('output', '');
  };

  // 列出课程
  const listCourses = async () => {
    addLine('output', '');
    addLine('success', '═══ 可用课程 ═══');
    
    setLoading(true);
    try {
      const response = await adminApi.getCourses();
      if (response.success && response.data) {
        response.data.forEach((course, index) => {
          addLine('output', `  [${index + 1}] ${course.code} - ${course.title}`);
        });
        addLine('output', '');
        addLine('output', '使用 optimize <课程代码> 运行优化');
      } else {
        addLine('error', '获取课程列表失败');
      }
    } catch (error) {
      addLine('error', '请求失败');
    }
    setLoading(false);
  };

  // 运行优化
  const runOptimization = async (args: string[]) => {
    if (args.length === 0) {
      addLine('warning', '用法: optimize <课程代码>');
      addLine('output', '输入 courses 查看可用课程');
      return;
    }

    const courseId = args[0];
    setCurrentCourse(courseId);
    
    addLine('output', '');
    addLine('success', `═══ 开始优化测试: ${courseId} ═══`);
    addLine('output', '');
    addLine('output', '正在初始化测试环境...');
    addLine('output', '加载课程内容...');
    addLine('output', '准备分块策略...');
    addLine('output', '');
    
    setLoading(true);
    
    // 模拟进度
    const strategies = ['semantic_small', 'semantic_medium', 'semantic_large', 'fixed_small', 'fixed_medium', 'heading_based'];
    for (let i = 0; i < strategies.length; i++) {
      addLine('output', `  [${i + 1}/${strategies.length}] 测试策略: ${strategies[i]}...`);
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    try {
      const response = await adminApi.runOptimization(courseId);
      if (response.success && response.data) {
        setOptimizationResult(response.data);
        
        addLine('output', '');
        addLine('success', '═══ 测试结果 ═══');
        addLine('output', '');
        
        // 显示各策略结果
        Object.entries(response.data.strategy_results).forEach(([name, result]) => {
          const strategyResult = result as StrategyResult;
          const bar = generateProgressBar(strategyResult.avg_recall);
          addLine('output', `  ${name.padEnd(20)} 召回率: ${bar} ${(strategyResult.avg_recall * 100).toFixed(1)}%`);
          addLine('output', `  ${' '.repeat(20)} 分块数: ${strategyResult.chunk_count}, 平均大小: ${strategyResult.avg_chunk_size.toFixed(0)}`);
          addLine('output', '');
        });
        
        addLine('success', `  ★ 推荐策略: ${response.data.recommended_strategy}`);
        addLine('output', '');
        addLine('output', response.data.summary);
        addLine('output', '');
      } else {
        addLine('error', `优化失败: ${response.error}`);
      }
    } catch (error) {
      addLine('error', '优化过程出错');
    }
    
    setLoading(false);
  };

  // 显示比较结果
  const showComparison = () => {
    if (!optimizationResult) {
      addLine('warning', '请先运行 optimize 命令获取优化结果');
      return;
    }
    
    addLine('output', '');
    addLine('success', '═══ 策略比较 ═══');
    addLine('output', '');
    
    const results = Object.entries(optimizationResult.strategy_results)
      .map(([name, result]) => ({
        name,
        recall: (result as StrategyResult).avg_recall,
        chunks: (result as StrategyResult).chunk_count,
        avgSize: (result as StrategyResult).avg_chunk_size,
      }))
      .sort((a, b) => b.recall - a.recall);
    
    addLine('output', '  策略名称             召回率    分块数    平均大小');
    addLine('output', '  ─────────────────────────────────────────────────');
    
    results.forEach((r, i) => {
      const rank = i === 0 ? '★' : ' ';
      addLine('output', `${rank} ${r.name.padEnd(20)} ${(r.recall * 100).toFixed(1).padStart(5)}%   ${r.chunks.toString().padStart(5)}   ${r.avgSize.toFixed(0).padStart(8)}`);
    });
    
    addLine('output', '');
  };

  // 显示配置
  const showConfig = async (args: string[]) => {
    addLine('output', '');
    addLine('success', '═══ RAG 配置 ═══');
    addLine('output', '');
    
    try {
      const response = await adminApi.getRAGConfig();
      if (response.success && response.data) {
        addLine('output', JSON.stringify(response.data, null, 2).split('\n').map(line => `  ${line}`).join('\n'));
      }
    } catch (error) {
      addLine('error', '获取配置失败');
    }
    
    addLine('output', '');
  };

  // 列出模型
  const listModels = async () => {
    addLine('output', '');
    addLine('success', '═══ 可用 Embedding 模型 ═══');
    addLine('output', '');
    
    try {
      const response = await adminApi.getEmbeddingModels();
      if (response.success && response.data) {
        response.data.forEach(model => {
          addLine('output', `  [${model.key}]`);
          addLine('output', `      名称: ${model.name}`);
          addLine('output', `      描述: ${model.description}`);
          addLine('output', '');
        });
      }
    } catch (error) {
      addLine('error', '获取模型列表失败');
    }
  };

  // 生成进度条
  const generateProgressBar = (value: number, width: number = 20): string => {
    const filled = Math.round(value * width);
    const empty = width - filled;
    return '█'.repeat(filled) + '░'.repeat(empty);
  };

  // 处理输入
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    
    setHistory(prev => [...prev, input]);
    setHistoryIndex(-1);
    handleCommand(input);
    setInput('');
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0) {
        const newIndex = historyIndex < history.length - 1 ? historyIndex + 1 : historyIndex;
        setHistoryIndex(newIndex);
        setInput(history[history.length - 1 - newIndex] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(history[history.length - 1 - newIndex] || '');
      } else {
        setHistoryIndex(-1);
        setInput('');
      }
    } else if (e.key === 'Tab') {
      e.preventDefault();
      // 自动补全
      const partial = input.toLowerCase();
      const matches = Object.keys(COMMANDS).filter(cmd => cmd.startsWith(partial));
      if (matches.length === 1) {
        setInput(matches[0] + ' ');
      } else if (matches.length > 1) {
        addLine('output', matches.join('  '));
      }
    }
  };

  // 聚焦输入框
  const focusInput = () => {
    inputRef.current?.focus();
  };

  return (
    <div className="space-y-4">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold text-cyan-400 font-mono">
          &gt;_ RAG Expert Console
        </h1>
        <p className="text-gray-500 text-sm mt-1 font-mono">
          自适应RAG策略优化工具 - CLI交互模式
        </p>
      </div>

      {/* 终端 */}
      <div 
        className="terminal min-h-[500px] cursor-text"
        onClick={focusInput}
        ref={terminalRef}
      >
        {/* 历史输出 */}
        {lines.map((line, index) => (
          <div 
            key={index} 
            className={`terminal-line ${
              line.type === 'input' ? 'text-cyan-400' :
              line.type === 'error' ? 'text-red-400' :
              line.type === 'success' ? 'text-green-400' :
              line.type === 'warning' ? 'text-yellow-400' :
              line.type === 'system' ? 'text-gray-500' :
              'text-gray-300'
            }`}
            style={{ whiteSpace: 'pre-wrap' }}
          >
            {line.content}
          </div>
        ))}

        {/* 加载指示器 */}
        {loading && (
          <div className="terminal-line text-yellow-400">
            <span className="loading-dots">处理中</span>
          </div>
        )}

        {/* 输入行 */}
        <form onSubmit={handleSubmit} className="terminal-line flex">
          <span className="terminal-prompt">{currentCourse || 'rag'}&gt;</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="terminal-input"
            autoFocus
            spellCheck={false}
          />
          <span className={`cursor-blink ${loading ? 'hidden' : ''}`}>▌</span>
        </form>
      </div>

      {/* 快捷键提示 */}
      <div className="flex justify-between text-gray-500 text-xs font-mono">
        <div>
          <span className="mr-4">↑/↓: 历史命令</span>
          <span className="mr-4">Tab: 自动补全</span>
          <span>Enter: 执行</span>
        </div>
        <div>
          输入 help 获取帮助
        </div>
      </div>
    </div>
  );
}
