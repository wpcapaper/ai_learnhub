'use client';

import React, { useEffect, useState } from 'react';

// 扩展Window接口以支持katex属性
declare global {
  interface Window {
    katex?: any;
  }
}

interface LaTeXRendererProps {
  content: string;
}

export default function LaTeXRenderer({ content }: LaTeXRendererProps) {
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const loadKaTeX = async () => {
      if (typeof window !== 'undefined' && !window.katex) {
        try {
          // @ts-ignore
          const katexModule = await import('katex');
          (window as any).katex = katexModule;
          setIsLoaded(true);
        } catch (error) {
          console.error('Failed to load KaTeX:', error);
        }
      } else {
        setIsLoaded(true);
      }
    };

    loadKaTeX();
  }, []);

  if (!content) {
    return <span className="text-gray-900"></span>;
  }

  if (!isLoaded) {
    return <span className="text-gray-900">{content}</span>;
  }

  const renderLatex = (latex: string, displayMode: boolean = false): React.ReactNode => {
    try {
      const katex = (window as any).katex;
      if (!katex) {
        return <span className="font-mono">{latex}</span>;
      }

      const html = katex.renderToString(latex, {
        displayMode,
        throwOnError: false,
      });

      return (
        <span
          dangerouslySetInnerHTML={{ __html: html }}
          style={displayMode ? { display: 'block', margin: '0.5em 0' } : {}}
        />
      );
    } catch (error) {
      console.error('LaTeX render error:', error);
      return <span className="font-mono">{latex}</span>;
    }
  };

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;

  const blockMathRegex = /\$\$([^$]+)\$\$/g;
  let match;

  while ((match = blockMathRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.substring(lastIndex, match.index));
    }
    parts.push(renderLatex(match[1], true));
    lastIndex = match.index + match[0].length;
  }

  const processInlineMath = (text: string): React.ReactNode[] => {
    const inlineParts: React.ReactNode[] = [];
    let inlineLastIndex = 0;
    let inlineMatch;
    const inlineMathRegex = /\$([^$]+)\$/g;

    while ((inlineMatch = inlineMathRegex.exec(text)) !== null) {
      if (inlineMatch.index > inlineLastIndex) {
        inlineParts.push(text.substring(inlineLastIndex, inlineMatch.index));
      }
      inlineParts.push(renderLatex(inlineMatch[1], false));
      inlineLastIndex = inlineMatch.index + inlineMatch[0].length;
    }

    if (inlineLastIndex < text.length) {
      inlineParts.push(text.substring(inlineLastIndex));
    }

    return inlineParts;
  };

  const finalParts: React.ReactNode[] = [];

  for (const part of parts) {
    if (typeof part === 'string') {
      const processed = processInlineMath(part);
      if (processed.length > 0) {
        finalParts.push(...processed);
      }
    } else {
      finalParts.push(part);
    }
  }

  if (lastIndex < content.length) {
    const remaining = content.substring(lastIndex);
    const processed = processInlineMath(remaining);
    if (processed.length > 0) {
      finalParts.push(...processed);
    }
  }

  return (
    <span className="text-gray-900">
      {finalParts.map((part, index) => {
        if (typeof part === 'string') {
          return <React.Fragment key={`text-${index}`}>{part}</React.Fragment>;
        }
        return <React.Fragment key={index}>{part}</React.Fragment>;
      })}
    </span>
  );
}
