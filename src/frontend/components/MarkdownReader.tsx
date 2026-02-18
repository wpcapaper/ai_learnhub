'use client';

import { useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import LaTeXRenderer from './LaTeXRenderer';

interface MarkdownReaderProps {
  content: string;
  onProgressChange?: (position: number, percentage: number) => void;
  variant?: 'document' | 'chat';
}

export default function MarkdownReader({ content, onProgressChange, variant = 'document' }: MarkdownReaderProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  // 跟踪滚动位置和阅读进度
  const handleScroll = () => {
    if (variant === 'chat' || !contentRef.current) return;

    const element = contentRef.current;
    const scrollTop = element.scrollTop;
    const scrollHeight = element.scrollHeight - element.clientHeight;
    const percentage = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;

    if (onProgressChange) {
      onProgressChange(scrollTop, percentage);
    }
  };

  if ((!content || content.trim() === '') && variant === 'document') {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">没有可显示的内容</p>
      </div>
    );
  }

  if ((!content || content.trim() === '') && variant === 'chat') {
    return null;
  }

  const containerClasses = variant === 'document' 
    ? "flex-1 overflow-y-auto px-8 py-6 markdown-content"
    : "markdown-content";

  return (
    <div
      ref={contentRef}
      onScroll={handleScroll}
      className={containerClasses}
      style={variant === 'document' ? { scrollBehavior: 'smooth' } : {}}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 代码块语法高亮
          code({ node, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';
            const inline = (props as any).inline || className?.includes('language-') === false;
            return !inline ? (
              <div className="bg-slate-100 rounded-lg my-4 overflow-x-auto">
                <SyntaxHighlighter
                  language={language}
                  PreTag="div"
                  className="rounded-lg p-4 !bg-transparent"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              </div>
            ) : (
              <code className="bg-slate-200 px-1.5 py-0.5 rounded text-sm" {...props}>
                {children}
              </code>
            );
          },
          // 自定义标题样式
          h1: ({ children }) => <h1 className="text-2xl font-bold mb-6 text-slate-900 border-b-2 border-slate-200 pb-3">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-bold mb-4 mt-8 text-slate-800">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-bold mb-3 mt-6 text-slate-800">{children}</h3>,
          // 自定义段落样式 - 集成 LaTeX
          p: ({ children }) => {
            return (
              <p className={`mb-4 text-slate-700 leading-relaxed ${variant === 'chat' ? 'text-sm' : ''}`}>
                {Array.isArray(children) 
                  ? children.map((child, i) => typeof child === 'string' ? <LaTeXRenderer key={i} content={child} /> : child)
                  : typeof children === 'string' ? <LaTeXRenderer content={children} /> : children
                }
              </p>
            );
          },
          // 自定义列表样式
          ul: ({ children }) => <ul className="mb-4 ml-6 list-disc text-slate-700">{children}</ul>,
          ol: ({ children }) => <ol className="mb-4 ml-6 list-decimal text-slate-700">{children}</ol>,
          li: ({ children }) => (
            <li className="mb-2">
              {Array.isArray(children) 
                  ? children.map((child, i) => typeof child === 'string' ? <LaTeXRenderer key={i} content={child} /> : child)
                  : typeof children === 'string' ? <LaTeXRenderer content={children} /> : children
              }
            </li>
          ),
          // 自定义链接样式
          a: ({ href, children }) => <a href={href} className="text-indigo-600 hover:text-indigo-800 underline">{children}</a>,
          // 自定义引用样式
          blockquote: ({ children }) => <blockquote className="border-l-4 border-slate-300 pl-4 italic my-4 text-slate-600">{children}</blockquote>,
          // 表格样式支持
          table: ({ children }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full border-collapse border border-slate-300">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-slate-100">{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr className="border-b border-slate-200">{children}</tr>,
          th: ({ children }) => <th className="border border-slate-300 px-4 py-2 text-left font-semibold text-slate-800">{children}</th>,
          td: ({ children }) => (
            <td className="border border-slate-300 px-4 py-2 text-slate-700">
              {Array.isArray(children) 
                ? children.map((child, i) => typeof child === 'string' ? <LaTeXRenderer key={i} content={child} /> : child)
                : typeof children === 'string' ? <LaTeXRenderer content={children} /> : children
              }
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
