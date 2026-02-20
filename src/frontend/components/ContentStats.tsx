'use client';

/**
 * 内容统计组件
 * 
 * 功能：
 * 1. 统计 Markdown 内容的字数（中文字符数）
 * 2. 计算预计阅读时间（按 300 字/分钟计算）
 * 3. 在章节顶部展示统计信息，帮助学习者了解内容规模
 */

interface ContentStatsProps {
  /** Markdown 内容字符串 */
  content: string;
}

/**
 * 从 Markdown 内容中提取纯文本并统计字数
 * 
 * 处理逻辑：
 * 1. 移除代码块（```包裹的内容）
 * 2. 移除行内代码（`包裹的内容）
 * 3. 移除 Markdown 标记符号（#、*、- 等）
 * 4. 统计中文字符数和英文单词数
 * 
 * @param content - Markdown 内容
 * @returns 字数统计结果
 */
function countWords(content: string): { chineseChars: number; englishWords: number; total: number } {
  // 移除代码块
  let text = content.replace(/```[\s\S]*?```/g, '');
  
  // 移除行内代码
  text = text.replace(/`[^`]+`/g, '');
  
  // 移除 LaTeX 公式
  text = text.replace(/\$\$[\s\S]*?\$\$/g, ''); // 块级公式
  text = text.replace(/\$[^$]+\$/g, ''); // 行内公式
  
  // 移除 Markdown 链接语法，保留文字
  text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  
  // 移除图片语法
  text = text.replace(/!\[[^\]]*\]\([^)]+\)/g, '');
  
  // 移除 HTML 标签
  text = text.replace(/<[^>]+>/g, '');
  
  // 移除 Markdown 标题标记
  text = text.replace(/^#+\s+/gm, '');
  
  // 移除 Markdown 列表标记
  text = text.replace(/^[\s]*[-*+]\s+/gm, '');
  text = text.replace(/^[\s]*\d+\.\s+/gm, '');
  
  // 移除 Markdown 引用标记
  text = text.replace(/^>\s*/gm, '');
  
  // 移除 Markdown 分隔线
  text = text.replace(/^[-*_]{3,}$/gm, '');
  
  // 移除加粗和斜体标记
  text = text.replace(/[*_]{1,3}([^*_]+)[*_]{1,3}/g, '$1');
  
  // 统计中文字符数
  const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
  
  // 统计英文单词数（连续的字母视为一个单词）
  const englishWords = (text.match(/[a-zA-Z]+/g) || []).length;
  
  // 总字数 = 中文字符数 + 英文单词数
  // 英文单词按 1 个字计算，与中文统计方式一致
  const total = chineseChars + englishWords;
  
  return { chineseChars, englishWords, total };
}

/**
 * 计算预计阅读时间
 * 
 * 阅读速度假设：
 * - 中文阅读速度：约 300 字/分钟
 * - 英文阅读速度：约 200 词/分钟
 * 
 * 取较慢的速度作为基准，确保预估时间充足
 * 
 * @param wordCount - 字数统计结果
 * @returns 预计阅读时间（分钟）
 */
function calculateReadingTime(wordCount: { chineseChars: number; englishWords: number; total: number }): number {
  const readingSpeed = 300; // 字/分钟
  const minutes = Math.ceil(wordCount.total / readingSpeed);
  return Math.max(1, minutes); // 至少 1 分钟
}

/**
 * 格式化字数显示
 * 超过 1000 字显示为 "X.Xk" 格式
 */
function formatWordCount(count: number): string {
  if (count >= 10000) {
    return `${(count / 10000).toFixed(1)}万`;
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}k`;
  }
  return count.toString();
}

export default function ContentStats({ content }: ContentStatsProps) {
  const wordCount = countWords(content);
  const readingTime = calculateReadingTime(wordCount);
  
  return (
    <div 
      className="flex items-center gap-4 text-sm"
      style={{ color: 'var(--foreground-secondary)' }}
    >
      {/* 字数统计 */}
      <div className="flex items-center gap-1.5">
        <svg 
          className="w-4 h-4" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
          style={{ opacity: 0.7 }}
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={1.5} 
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
          />
        </svg>
        <span>字数: {formatWordCount(wordCount.total)}</span>
      </div>
      
      {/* 分隔符 */}
      <span style={{ color: 'var(--card-border)' }}>|</span>
      
      {/* 预计用时 */}
      <div className="flex items-center gap-1.5">
        <svg 
          className="w-4 h-4" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
          style={{ opacity: 0.7 }}
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={1.5} 
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" 
          />
        </svg>
        <span>约 {readingTime} 分钟</span>
      </div>
    </div>
  );
}
