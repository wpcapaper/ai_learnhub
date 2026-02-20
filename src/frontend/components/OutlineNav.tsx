'use client';

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

interface OutlineItem {
  id: string;
  level: number;
  text: string;
}

interface OutlineNavProps {
  content: string;
  scrollContainer: HTMLDivElement | null;
  visible?: boolean;
}

/**
 * 将标题文本转换为 slug ID
 * 必须与 MarkdownReader.tsx 中的 slugify 函数保持一致
 */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 50);
}

function extractHeadings(content: string): OutlineItem[] {
  const headings: OutlineItem[] = [];
  
  const contentWithoutCode = content
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]+`/g, '');
  
  const headingRegex = /^(#{1,3})\s+(.+?)(?:\s+#+)?$/gm;
  
  let match;
  while ((match = headingRegex.exec(contentWithoutCode)) !== null) {
    const level = match[1].length;
    const text = match[2].trim();
    const slug = slugify(text);
    const id = `heading-${headings.length}-${slug || 'untitled'}`;
    
    headings.push({
      id,
      level,
      text,
    });
  }
  
  return headings;
}

export default function OutlineNav({ content, scrollContainer, visible = true }: OutlineNavProps) {
  const headings = useMemo(() => extractHeadings(content), [content]);
  
  const [activeId, setActiveId] = useState<string>('');
  
  const headingPositionsRef = useRef<Map<string, number>>(new Map());
  
  const updateHeadingPositions = useCallback(() => {
    if (!scrollContainer) return;
    
    const container = scrollContainer;
    const newPositions = new Map<string, number>();
    
    container.querySelectorAll('h1[id], h2[id], h3[id]').forEach((el) => {
      const id = el.id;
      const relativeTop = el.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop;
      newPositions.set(id, relativeTop);
    });
    
    headingPositionsRef.current = newPositions;
  }, [scrollContainer]);
  
  const handleScroll = useCallback(() => {
    if (!scrollContainer) return;
    
    const container = scrollContainer;
    const scrollTop = container.scrollTop;
    
    if (headingPositionsRef.current.size === 0) {
      updateHeadingPositions();
    }
    
    let currentId = '';
    let minDistance = Infinity;
    
    headingPositionsRef.current.forEach((position, id) => {
      const distance = Math.abs(position - scrollTop - 50);
      if (position <= scrollTop + 100 && distance < minDistance) {
        minDistance = distance;
        currentId = id;
      }
    });
    
    if (currentId && currentId !== activeId) {
      setActiveId(currentId);
    }
  }, [scrollContainer, activeId, updateHeadingPositions]);
  
  useEffect(() => {
    const timer = setTimeout(updateHeadingPositions, 100);
    
    const container = scrollContainer;
    if (container) {
      container.addEventListener('scroll', handleScroll);
    }
    
    return () => {
      clearTimeout(timer);
      if (container) {
        container.removeEventListener('scroll', handleScroll);
      }
    };
  }, [scrollContainer, handleScroll, updateHeadingPositions]);
  
  useEffect(() => {
    updateHeadingPositions();
  }, [content, updateHeadingPositions]);
  
  const scrollToHeading = useCallback((headingId: string) => {
    if (!scrollContainer) return;
    
    const container = scrollContainer;
    
    const headingEl = container.querySelector(`h1[id="${headingId}"], h2[id="${headingId}"], h3[id="${headingId}"]`);
    
    if (headingEl) {
      const containerRect = container.getBoundingClientRect();
      const headingRect = headingEl.getBoundingClientRect();
      const targetScrollTop = container.scrollTop + (headingRect.top - containerRect.top) - 20;
      
      container.scrollTo({
        top: targetScrollTop,
        behavior: 'smooth',
      });
      
      setActiveId(headingId);
    }
  }, [scrollContainer]);
  
  if (headings.length === 0 || !visible) {
    return null;
  }
  
  return (
    <nav 
      className="flex flex-col h-full"
      style={{ 
        background: 'var(--card-bg)',
      }}
    >
      {/* 标题 */}
      <div 
        className="px-3 py-2 border-b text-sm font-medium"
        style={{ 
          borderColor: 'var(--card-border)',
          color: 'var(--foreground-title)',
        }}
      >
        目录
      </div>
      
      {/* 大纲列表 */}
      <div className="flex-1 overflow-y-auto py-2">
        {headings.map((heading, index) => {
          // 根据标题级别计算缩进
          const indentLevel = heading.level - 1;
          const paddingLeft = 12 + indentLevel * 12;
          
          const isActive = activeId === heading.id;
          
          return (
            <button
              key={`${heading.id}-${index}`}
              onClick={() => scrollToHeading(heading.id)}
              className="w-full text-left py-1.5 text-sm transition-colors truncate"
              style={{
                paddingLeft: `${paddingLeft}px`,
                paddingRight: '12px',
                color: isActive ? 'var(--primary)' : 'var(--foreground-secondary)',
                background: isActive ? 'var(--primary-bg)' : 'transparent',
                borderLeft: isActive ? '2px solid var(--primary)' : '2px solid transparent',
              }}
              title={heading.text}
            >
              {heading.text}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
