'use client';

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

/**
 * 大纲标题项接口
 */
interface OutlineItem {
  id: string;           // 标题 ID，用于滚动定位
  level: number;        // 标题级别 (1-3)
  text: string;         // 标题文本
}

interface OutlineNavProps {
  /** Markdown 内容，用于提取标题 */
  content: string;
  /** 滚动容器，用于控制滚动 */
  scrollContainer: HTMLDivElement | null;
  /** 是否显示大纲（响应式控制） */
  visible?: boolean;
}

/**
 * 从 Markdown 内容中提取标题列表
 * 
 * 处理逻辑：
 * 1. 使用正则匹配 h1/h2/h3 标题
 * 2. 生成唯一 ID 用于锚点定位
 * 3. 过滤掉代码块内的标题
 * 
 * @param content - Markdown 内容
 * @returns 标题列表
 */
function extractHeadings(content: string): OutlineItem[] {
  const headings: OutlineItem[] = [];
  
  // 先移除代码块，避免匹配代码块内的标题
  const contentWithoutCode = content
    .replace(/```[\s\S]*?```/g, '')  // 移除代码块
    .replace(/`[^`]+`/g, '');        // 移除行内代码
  
  // 匹配 h1-h3 标题
  // 支持 # 风格和 ===/--- 风格
  const headingRegex = /^(#{1,3})\s+(.+?)(?:\s+#+)?$/gm;
  
  let match;
  while ((match = headingRegex.exec(contentWithoutCode)) !== null) {
    const level = match[1].length;
    const text = match[2].trim();
    
    // 生成唯一 ID：使用标题文本的哈希或索引
    const id = `heading-${headings.length}-${text.slice(0, 10).replace(/\s+/g, '-')}`;
    
    headings.push({
      id,
      level,
      text,
    });
  }
  
  return headings;
}

/**
 * 大纲导航组件
 * 
 * 功能：
 * 1. 自动提取 Markdown 的 h1/h2/h3 标题作为大纲
 * 2. 点击标题可滚动到对应位置
 * 3. 高亮当前滚动位置的标题
 */
export default function OutlineNav({ content, scrollContainer, visible = true }: OutlineNavProps) {
  // 提取标题列表（使用 useMemo 避免重复计算）
  const headings = useMemo(() => extractHeadings(content), [content]);
  
  // 当前激活的标题 ID
  const [activeId, setActiveId] = useState<string>('');
  
  // 标题元素位置缓存
  const headingPositionsRef = useRef<Map<string, number>>(new Map());
  
  /**
   * 更新标题元素的位置缓存
   * 在内容变化或窗口大小变化时调用
   */
  const updateHeadingPositions = useCallback(() => {
    if (!scrollContainer) return;
    
    const container = scrollContainer;
    const newPositions = new Map<string, number>();
    
    // 遍历所有标题元素，记录它们在容器内的位置
    container.querySelectorAll('h1[id], h2[id], h3[id]').forEach((el) => {
      const id = el.id;
      // 计算元素相对于滚动容器顶部的位置
      const relativeTop = el.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop;
      newPositions.set(id, relativeTop);
    });
    
    headingPositionsRef.current = newPositions;
  }, [scrollContainer]);
  
  /**
   * 处理滚动事件，更新当前激活的标题
   */
  const handleScroll = useCallback(() => {
    if (!scrollContainer) return;
    
    const container = scrollContainer;
    const scrollTop = container.scrollTop;
    
    // 更新位置缓存
    if (headingPositionsRef.current.size === 0) {
      updateHeadingPositions();
    }
    
    // 找到当前滚动位置对应的标题
    let currentId = '';
    let minDistance = Infinity;
    
    headingPositionsRef.current.forEach((position, id) => {
      // 标题在视口上方或接近顶部时激活
      const distance = Math.abs(position - scrollTop - 50); // 50px 偏移量
      if (position <= scrollTop + 100 && distance < minDistance) {
        minDistance = distance;
        currentId = id;
      }
    });
    
    if (currentId && currentId !== activeId) {
      setActiveId(currentId);
    }
  }, [scrollContainer, activeId, updateHeadingPositions]);
  
  // 初始化位置缓存并监听滚动
  useEffect(() => {
    // 延迟更新位置，等待 DOM 渲染完成
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
  
  // 内容变化时重新计算位置
  useEffect(() => {
    updateHeadingPositions();
  }, [content, updateHeadingPositions]);
  
  /**
   * 点击标题时滚动到对应位置
   */
  const scrollToHeading = useCallback((headingId: string) => {
    if (!scrollContainer) return;
    
    const container = scrollContainer;
    
    // 尝试直接查找带 ID 的标题元素
    const headingEl = container.querySelector(`h1[id="${headingId}"], h2[id="${headingId}"], h3[id="${headingId}"]`);
    
    if (headingEl) {
      // 计算目标滚动位置
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
  
  // 没有标题时不显示
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
