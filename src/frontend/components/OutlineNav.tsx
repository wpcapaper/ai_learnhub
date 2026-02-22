'use client';

import { useState, useEffect, useMemo, useRef } from 'react';

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
    headings.push({
      id: `heading-${headings.length}-${slug || 'untitled'}`,
      level,
      text,
    });
  }
  return headings;
}

export default function OutlineNav({ content, scrollContainer, visible = true }: OutlineNavProps) {
  const headings = useMemo(() => extractHeadings(content), [content]);
  const [activeId, setActiveId] = useState<string>('');
  
  // 用 ref 存储最新的 scrollContainer
  const containerRef = useRef<HTMLDivElement | null>(null);
  containerRef.current = scrollContainer;

  // 滚动事件处理
  useEffect(() => {
    const container = scrollContainer;
    if (!container) return;

    const onScroll = () => {
      const el = containerRef.current;
      if (!el) return;
      
      const headingEls = el.querySelectorAll('h1[id], h2[id], h3[id]');
      let currentId = '';
      
      headingEls.forEach((heading) => {
        const rect = heading.getBoundingClientRect();
        const containerRect = el.getBoundingClientRect();
        const relativeTop = rect.top - containerRect.top;
        
        if (relativeTop <= 80) {
          currentId = heading.id;
        }
      });
      
      setActiveId(prev => currentId && currentId !== prev ? currentId : prev);
    };

    container.addEventListener('scroll', onScroll, { passive: true });
    onScroll(); // 初始化
    
    return () => {
      container.removeEventListener('scroll', onScroll);
    };
  }, [scrollContainer]);

  // 点击跳转
  const handleItemClick = (headingId: string) => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    
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
  };

  if (headings.length === 0 || !visible) {
    return null;
  }

  return (
    <nav className="flex flex-col h-full" style={{ background: 'var(--card-bg)' }}>
      <div 
        className="px-3 py-2 border-b text-sm font-medium"
        style={{ borderColor: 'var(--card-border)', color: 'var(--foreground-title)' }}
      >
        目录
      </div>
      
      <div className="flex-1 overflow-y-auto py-2">
        {headings.map((heading, index) => {
          const indentLevel = heading.level - 1;
          const paddingLeft = 12 + indentLevel * 12;
          const isActive = activeId === heading.id;
          
          return (
            <button
              key={`${heading.id}-${index}`}
              onClick={() => handleItemClick(heading.id)}
              className="w-full text-left py-1.5 text-sm truncate"
              style={{
                paddingLeft: `${paddingLeft}px`,
                paddingRight: '12px',
                color: isActive ? 'var(--primary)' : 'var(--foreground-secondary)',
                background: isActive ? 'var(--primary-bg)' : 'transparent',
                borderLeft: isActive ? '2px solid var(--primary)' : '2px solid transparent',
                cursor: 'pointer',
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
