'use client';

import { useRef, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import LaTeXRenderer from './LaTeXRenderer';

interface MarkdownReaderProps {
  content: string;
  onProgressChange?: (position: number, percentage: number) => void;
  variant?: 'document' | 'chat';
  courseDirName?: string;
  chapterPath?: string;
}

function MermaidDiagram({ code }: { code: string }) {
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    
    const renderDiagram = async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        
        // 检测当前主题：优先 data-theme 属性，其次 dark class
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || 
                       document.documentElement.classList.contains('dark');
        
        mermaid.initialize({
          startOnLoad: false,
          theme: isDark ? 'dark' : 'default',
          fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        });
        
        const { svg } = await mermaid.render('mermaid-' + Date.now(), code);
        if (mounted) {
          setSvg(svg);
          setIsLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError('图表渲染失败');
          setIsLoading(false);
        }
      }
    };
    
    renderDiagram();
    
    return () => { mounted = false; };
  }, [code]);

  if (isLoading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: 'var(--foreground-secondary)' }}>
        加载图表中...
      </div>
    );
  }

  if (error) {
    return (
      <pre style={{ 
        background: 'var(--code-bg)', 
        color: 'var(--code-text)',
        padding: '16px',
        borderRadius: 'var(--radius-md)',
        overflow: 'auto'
      }}>
        {code}
      </pre>
    );
  }

  return (
    <div 
      style={{ 
        padding: '16px', 
        background: 'var(--background-secondary)', 
        borderRadius: 'var(--radius-md)',
        overflow: 'auto'
      }}
      dangerouslySetInnerHTML={{ __html: svg }} 
    />
  );
}

export default function MarkdownReader({ content, onProgressChange, variant = 'document', courseDirName, chapterPath }: MarkdownReaderProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  
  const rewriteImageUrl = (src: string): string => {
    if (src.startsWith('http://') || src.startsWith('https://') || src.startsWith('/')) {
      return src;
    }
    if (!courseDirName || !chapterPath) {
      return src;
    }
    const chapterDir = chapterPath.includes('/') ? chapterPath.substring(0, chapterPath.lastIndexOf('/')) : '';
    const basePath = chapterDir ? `${courseDirName}/${chapterDir}` : courseDirName;
    return `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/courses/${basePath}/${src}`;
  };

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
      <div className="flex-1 flex items-center justify-center" style={{ background: 'var(--background-secondary)' }}>
        <p style={{ color: 'var(--foreground-secondary)' }}>没有可显示的内容</p>
      </div>
    );
  }

  if ((!content || content.trim() === '') && variant === 'chat') {
    return null;
  }

  const containerClasses = variant === 'document' 
    ? "flex-1 overflow-y-auto px-8 py-6 markdown-content"
    : "markdown-content";

  const baseFontSize = variant === 'document' ? 17 : 14;

  return (
    <div
      ref={contentRef}
      onScroll={handleScroll}
      className={containerClasses}
      style={variant === 'document' ? { scrollBehavior: 'smooth', fontSize: baseFontSize } : { fontSize: baseFontSize }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }: any) {
            return <>{children}</>;
          },
          code({ className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';
            const inline = !(props as any).node?.position?.start?.line || 
                           (props as any).inline ||
                           !className?.includes('language-');
            
            if (inline) {
              return (
                <code 
                  style={{
                    background: 'var(--code-inline-bg)',
                    color: 'var(--code-text)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '0.85em',
                    textShadow: 'none',
                    boxShadow: 'none',
                  }}
                  {...props}
                >
                  {children}
                </code>
              );
            }
            
            const codeContent = String(children).replace(/\n$/, '');
            
            if (language === 'mermaid') {
              return (
                <div style={{ margin: '16px 0' }}>
                  <MermaidDiagram code={codeContent} />
                </div>
              );
            }
            
            const languageColors: Record<string, string> = {
              python: '#569cd6',
              javascript: '#f59e0b',
              typescript: '#3178c6',
              java: '#ed8b00',
              go: '#00add8',
              rust: '#dea584',
              cpp: '#f34b7d',
              c: '#555555',
              sql: '#e38c00',
              html: '#e34c26',
              css: '#264de4',
              json: '#cbcb41',
              yaml: '#cb171e',
              bash: '#89e051',
              shell: '#89e051',
            };
            const langColor = languageColors[language] || 'var(--code-lang-default)';
            
            return (
              <div style={{ margin: '16px 0' }}>
                {language && (
                  <div style={{
                    padding: '4px 12px',
                    background: 'var(--code-header-bg)',
                    border: '1px solid var(--code-border)',
                    borderBottom: 'none',
                    display: 'inline-block',
                  }}>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '12px',
                      color: langColor,
                      fontWeight: 500,
                    }}>{language}</span>
                  </div>
                )}
                <SyntaxHighlighter
                  language={language || 'text'}
                  PreTag="pre"
                  style={undefined}
                  customStyle={{
                    margin: 0,
                    padding: '16px',
                    background: 'var(--code-bg)',
                    border: '1px solid var(--code-border)',
                    borderTop: language ? 'none' : '1px solid var(--code-border)',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '14px',
                    lineHeight: 1.6,
                    color: 'var(--code-text)',
                    textShadow: 'none',
                    boxShadow: 'none',
                  }}
                  codeTagProps={{
                    style: {
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '14px',
                      textShadow: 'none',
                    }
                  }}
                  {...props}
                >
                  {codeContent}
                </SyntaxHighlighter>
              </div>
            );
          },
          h1: ({ children }) => (
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '1rem', color: 'var(--foreground-title)', borderBottom: '1px solid var(--card-border)', paddingBottom: '0.75rem' }}>
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.75rem', marginTop: '1.5rem', color: 'var(--foreground-title)' }}>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', marginTop: '1rem', color: 'var(--foreground-title)' }}>
              {children}
            </h3>
          ),
          p: ({ children }) => {
            return (
              <p style={{ marginBottom: '1rem', color: 'var(--foreground)', lineHeight: 1.8 }}>
                {Array.isArray(children) 
                  ? children.map((child, i) => typeof child === 'string' ? <LaTeXRenderer key={i} content={child} /> : child)
                  : typeof children === 'string' ? <LaTeXRenderer content={children} /> : children
                }
              </p>
            );
          },
          ul: ({ children }) => <ul style={{ marginBottom: '1rem', marginLeft: '1.5rem', listStyleType: 'disc', color: 'var(--foreground)' }}>{children}</ul>,
          ol: ({ children }) => <ol style={{ marginBottom: '1rem', marginLeft: '1.5rem', listStyleType: 'decimal', color: 'var(--foreground)' }}>{children}</ol>,
          li: ({ children }) => (
            <li style={{ marginBottom: '0.25rem', lineHeight: 1.7 }}>
              {Array.isArray(children) 
                  ? children.map((child, i) => typeof child === 'string' ? <LaTeXRenderer key={i} content={child} /> : child)
                  : typeof children === 'string' ? <LaTeXRenderer content={children} /> : children
              }
            </li>
          ),
          a: ({ href, children }) => <a href={href} style={{ color: 'var(--primary)' }}>{children}</a>,
          img: ({ src, alt }) => (
            <img 
              src={rewriteImageUrl(typeof src === 'string' ? src : '')} 
              alt={alt || ''} 
              style={{ maxWidth: '100%', height: 'auto', borderRadius: 'var(--radius-md)', margin: '1rem 0' }}
              loading="lazy"
            />
          ),
          blockquote: ({ children }) => (
            <blockquote style={{ borderLeft: '3px solid var(--primary)', paddingLeft: '1rem', margin: '1rem 0', color: 'var(--foreground-secondary)', background: 'var(--background-secondary)', padding: '0.75rem 1rem' }}>
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div style={{ overflowX: 'auto', margin: '1rem 0' }}>
              <table style={{ minWidth: '100%', borderCollapse: 'collapse' }}>{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead style={{ background: 'var(--background-secondary)' }}>{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr style={{ borderBottom: '1px solid var(--card-border)' }}>{children}</tr>,
          th: ({ children }) => <th style={{ border: '1px solid var(--card-border)', padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--foreground-title)' }}>{children}</th>,
          td: ({ children }) => (
            <td style={{ border: '1px solid var(--card-border)', padding: '0.5rem 0.75rem', color: 'var(--foreground)' }}>
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