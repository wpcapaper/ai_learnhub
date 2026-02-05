'use client';

import { useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { apiClient } from '@/lib/api';

interface MarkdownReaderProps {
  content: string;
  onProgressChange?: (position: number, percentage: number) => void;
}

export default function MarkdownReader({ content, onProgressChange }: MarkdownReaderProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  // 跟踪滚动位置和阅读进度
  const handleScroll = () => {
    if (!contentRef.current) return;

    const element = contentRef.current;
    const scrollTop = element.scrollTop;
    const scrollHeight = element.scrollHeight - element.clientHeight;
    const percentage = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;

    if (onProgressChange) {
      onProgressChange(scrollTop, percentage);
    }
  };

  if (!content || content.trim() === '') {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">没有可显示的内容</p>
      </div>
    );
  }

  return (
    <div
      ref={contentRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-8 py-6 markdown-content"
      style={{ scrollBehavior: 'smooth' }}
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
              <div className="bg-gray-100 rounded-lg my-4 overflow-x-auto">
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
              <code className="bg-gray-200 px-1 py-0.5 rounded text-sm" {...props}>
                {children}
              </code>
            );
          },
          // 自定义标题样式
          h1: ({ children }) => <h1 className="text-3xl font-bold mb-6 text-gray-900 border-b-2 border-gray-200 pb-3">{children}</h1>,
          h2: ({ children }) => <h2 className="text-2xl font-bold mb-4 mt-8 text-gray-800">{children}</h2>,
          h3: ({ children }) => <h3 className="text-xl font-bold mb-3 mt-6 text-gray-800">{children}</h3>,
          // 自定义段落样式
          p: ({ children }) => <p className="mb-4 text-gray-700 leading-relaxed">{children}</p>,
          // 自定义列表样式
          ul: ({ children }) => <ul className="mb-4 ml-6 list-disc text-gray-700">{children}</ul>,
          ol: ({ children }) => <ol className="mb-4 ml-6 list-decimal text-gray-700">{children}</ol>,
          li: ({ children }) => <li className="mb-2">{children}</li>,
          // 自定义链接样式
          a: ({ href, children }) => <a href={href} className="text-blue-600 hover:text-blue-800 underline">{children}</a>,
          // 自定义引用样式
          blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic my-4 text-gray-600">{children}</blockquote>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
