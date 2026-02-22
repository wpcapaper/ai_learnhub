'use client';

import React, { useEffect, useState, useMemo, memo } from 'react';

declare global {
  interface Window {
    katex?: any;
  }
}

interface LaTeXRendererProps {
  content: string;
}

// 用 memo 包装，确保 props 不变时不重渲染
const LaTeXRenderer = memo(function LaTeXRenderer({ content }: LaTeXRendererProps) {
  const [katexLoaded, setKatexLoaded] = useState(false);

  useEffect(() => {
    const loadKaTeX = async () => {
      if (typeof window !== 'undefined' && !window.katex) {
        try {
          const katexModule = await import('katex');
          window.katex = katexModule;
          setKatexLoaded(true);
        } catch (error) {
          console.error('Failed to load KaTeX:', error);
        }
      } else {
        setKatexLoaded(true);
      }
    };
    loadKaTeX();
  }, []);

  // 缓存渲染结果，只有 content 或 katexLoaded 变化时才重新渲染
  const renderedHtml = useMemo(() => {
    if (!content || !katexLoaded) return null;

    const katex = window.katex;
    if (!katex) return content;

    const renderLatex = (latex: string, displayMode: boolean = false): string => {
      try {
        return katex.renderToString(latex, {
          displayMode,
          throwOnError: false,
        });
      } catch (error) {
        return latex;
      }
    };

    let result = content;
    
    // 先处理块级公式 $$...$$
    result = result.replace(/\$\$([^$]+)\$\$/g, (_, latex) => {
      const html = renderLatex(latex, true);
      return `<span style="display:block;margin:0.5em 0;">${html}</span>`;
    });
    
    // 再处理行内公式 $...$
    result = result.replace(/\$([^$]+)\$/g, (_, latex) => {
      const html = renderLatex(latex, false);
      return html;
    });

    return result;
  }, [content, katexLoaded]);

  if (!content) {
    return <span style={{ color: 'var(--foreground)' }} />;
  }

  if (!katexLoaded || !renderedHtml) {
    return <span style={{ color: 'var(--foreground)' }}>{content}</span>;
  }

  return (
    <span 
      style={{ color: 'var(--foreground)' }}
      dangerouslySetInnerHTML={{ __html: renderedHtml }}
    />
  );
});

export default LaTeXRenderer;
