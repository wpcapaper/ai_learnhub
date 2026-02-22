'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

interface OutlineItem {
  id: string;
  level: number;
  text: string;
}

interface OutlineNavProps {
  scrollContainer: HTMLDivElement | null;
  visible?: boolean;
}

export default function OutlineNav({ scrollContainer, visible = true }: OutlineNavProps) {
  const [headings, setHeadings] = useState<OutlineItem[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  
  const headingElsRef = useRef<Element[]>([]);
  const navListRef = useRef<HTMLDivElement | null>(null);
  const activeButtonRef = useRef<HTMLButtonElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  // 同步 scrollContainer 到 ref，供 useCallback 使用
  useEffect(() => {
    scrollContainerRef.current = scrollContainer;
  }, [scrollContainer]);

  // 从 DOM 中读取 headings
  useEffect(() => {
    const container = scrollContainer;
    if (!container) return;
    
    const updateHeadings = () => {
      const headingEls = container.querySelectorAll('h1[id], h2[id], h3[id]');
      headingElsRef.current = Array.from(headingEls);
      
      const newHeadings: OutlineItem[] = headingElsRef.current.map(el => ({
        id: el.id,
        level: parseInt(el.tagName.charAt(1)),
        text: el.textContent?.trim() || '',
      }));
      setHeadings(newHeadings);
    };
    
    updateHeadings();
    
    const observer = new MutationObserver(updateHeadings);
    observer.observe(container, { childList: true, subtree: true });
    
    return () => observer.disconnect();
  }, [scrollContainer]);

  // 当 activeId 变化时，自动滚动目录使当前项可见
  useEffect(() => {
    if (activeButtonRef.current && navListRef.current) {
      const button = activeButtonRef.current;
      const container = navListRef.current;
      
      const buttonRect = button.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      
      // 检查是否在视口内
      const isAbove = buttonRect.top < containerRect.top;
      const isBelow = buttonRect.bottom > containerRect.bottom;
      
      if (isAbove || isBelow) {
        button.scrollIntoView({
          block: 'nearest',
          behavior: 'smooth',
        });
      }
    }
  }, [activeId]);

  // 滚动事件处理 - 使用 RAF 节流
  useEffect(() => {
    const container = scrollContainer;
    if (!container) return;

    let rafId: number | null = null;

    const onScroll = () => {
      if (rafId) return; // 已有待处理的帧，跳过
      
      rafId = requestAnimationFrame(() => {
        rafId = null;
        const el = scrollContainerRef.current;
        if (!el) return;
        
        const containerRect = el.getBoundingClientRect();
        let currentId = '';
        let minDistance = Infinity;
        
        for (const heading of headingElsRef.current) {
          const rect = heading.getBoundingClientRect();
          const relativeTop = rect.top - containerRect.top;
          
          if (relativeTop <= 100 && Math.abs(relativeTop) < minDistance) {
            minDistance = Math.abs(relativeTop);
            currentId = heading.id;
          }
        }
        
        setActiveId(prev => currentId && currentId !== prev ? currentId : prev);
      });
    };

    container.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    
    return () => {
      container.removeEventListener('scroll', onScroll);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [scrollContainer]);

  // 点击跳转
  const handleItemClick = useCallback((headingId: string) => {
    const container = scrollContainerRef.current;
    if (!container) return;
    
    window.history.pushState(null, '', `#${headingId}`);
    setActiveId(headingId);
    
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
  }, []);

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
      
      <div ref={navListRef} className="flex-1 overflow-y-auto py-2">
        {headings.map((heading) => {
          const indentLevel = heading.level - 1;
          const paddingLeft = 12 + indentLevel * 12;
          const isActive = activeId === heading.id;
          
          return (
            <button
              key={heading.id}
              ref={isActive ? activeButtonRef : undefined}
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
