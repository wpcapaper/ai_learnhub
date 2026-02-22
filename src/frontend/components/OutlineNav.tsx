'use client';

import { useState, useEffect, useRef } from 'react';

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

export default function OutlineNav({ content, scrollContainer, visible = true }: OutlineNavProps) {
  const [headings, setHeadings] = useState<OutlineItem[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  
  const containerRef = useRef<HTMLDivElement | null>(null);
  containerRef.current = scrollContainer;

  // 从 DOM 中读取 headings
  useEffect(() => {
    const container = scrollContainer;
    if (!container) return;
    
    const updateHeadings = () => {
      const headingEls = container.querySelectorAll('h1[id], h2[id], h3[id]');
      const newHeadings: OutlineItem[] = Array.from(headingEls).map(el => ({
        id: el.id,
        level: parseInt(el.tagName.charAt(1)),
        text: el.textContent?.trim() || '',
      }));
      setHeadings(newHeadings);
    };
    
    // 初始读取
    updateHeadings();
    
    // 使用 MutationObserver 监听 DOM 变化
    const observer = new MutationObserver(updateHeadings);
    observer.observe(container, { childList: true, subtree: true });
    
    return () => observer.disconnect();
  }, [scrollContainer]);

  // 滚动事件处理
  useEffect(() => {
    const container = scrollContainer;
    if (!container) return;

    const onScroll = () => {
      const el = containerRef.current;
      if (!el) return;
      
      const headingEls = el.querySelectorAll('h1[id], h2[id], h3[id]');
      let currentId = '';
      let minDistance = Infinity;
      
      headingEls.forEach((heading) => {
        const rect = heading.getBoundingClientRect();
        const containerRect = el.getBoundingClientRect();
        const relativeTop = rect.top - containerRect.top;
        
        if (relativeTop <= 100 && Math.abs(relativeTop) < minDistance) {
          minDistance = Math.abs(relativeTop);
          currentId = heading.id;
        }
      });
      
      if (currentId && currentId !== activeId) {
        setActiveId(currentId);
      }
    };

    container.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    
    return () => {
      container.removeEventListener('scroll', onScroll);
    };
  }, [scrollContainer, activeId]);

  // 点击跳转
  const handleItemClick = (headingId: string) => {
    const container = containerRef.current;
    if (!container) return;
    
    // 更新 URL hash
    window.history.pushState(null, '', `#${headingId}`);
    setActiveId(headingId);
    
    // 查找并滚动到目标
    const targetEl = container.querySelector(`#${CSS.escape(headingId)}`);
    if (targetEl) {
      const containerRect = container.getBoundingClientRect();
      const headingRect = targetEl.getBoundingClientRect();
      const targetScrollTop = container.scrollTop + (headingRect.top - containerRect.top) - 20;
      
      container.scrollTo({
        top: targetScrollTop,
        behavior: 'smooth',
      });
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
        {headings.map((heading) => {
          const indentLevel = heading.level - 1;
          const paddingLeft = 12 + indentLevel * 12;
          const isActive = activeId === heading.id;
          
          return (
            <button
              key={heading.id}
              onClick={() => handleItemClick(heading.id)}
              className="w-full text-left py-1.5 text-sm truncate transition-all duration-150"
              style={{
                paddingLeft: `${paddingLeft}px`,
                paddingRight: '12px',
                color: isActive ? 'var(--primary)' : 'var(--foreground-secondary)',
                background: isActive ? 'var(--primary-bg)' : 'transparent',
                borderLeft: isActive ? '3px solid var(--primary)' : '3px solid transparent',
                fontWeight: isActive ? 600 : 400,
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
