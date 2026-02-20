'use client';

import { useState, useRef, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import MarkdownReader from './MarkdownReader';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface AIAssistantProps {
  chapterId: string;
  userId?: string;
}

 export default function AIAssistant({ chapterId, userId }: AIAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [thinkingText, setThinkingText] = useState('');
  const [showFollowUp, setShowFollowUp] = useState(false);
  
  const messageIdCounter = useRef(0);
  const generateMessageId = () => `msg_${Date.now()}_${++messageIdCounter.current}`;
  
  const targetContentRef = useRef('');
  const currentDisplayedContentRef = useRef('');
  const typingIntervalRef = useRef<any>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const userName = '我';
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);

  const THINKING_MESSAGES = [
    "AI 正在阅读课程内容...",
    "正在组织语言...",
    "正在检索相关知识点...",
    "正在构建回答逻辑..."
  ];

  useEffect(() => {
    return () => {
      if (typingIntervalRef.current) {
        clearInterval(typingIntervalRef.current);
        typingIntervalRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    let interval: any;
    if (isLoading && !isStreaming) {
      let i = 0;
      setThinkingText(THINKING_MESSAGES[0]);
      interval = setInterval(() => {
        i = (i + 1) % THINKING_MESSAGES.length;
        setThinkingText(THINKING_MESSAGES[i]);
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isLoading, isStreaming]);

  // 自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollTop = messagesEndRef.current.scrollHeight;
    }
  }, [messages]);

  // 发送消息
  const handleSendMessage = async () => {
    if (!input.trim() || isLoading || !userId) return;

    const userMessage: Message = {
      id: generateMessageId(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setShowFollowUp(false);
    setSuggestedQuestions([]);
    
    targetContentRef.current = '';
    currentDisplayedContentRef.current = '';
    
    const assistantMessageId = generateMessageId();
    setMessages(prev => [
      ...prev,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
      }
    ]);

    try {
      // 调用 AI 对话接口（流式响应）
      const stream = await apiClient.aiChatStream(chapterId, input, userId);
      setIsStreaming(true); // 开始流式传输（思考结束）
      
      const reader = stream.getReader();
      const decoder = new TextDecoder();

      if (typingIntervalRef.current) {
        clearInterval(typingIntervalRef.current);
        typingIntervalRef.current = null;
      }
      
      targetContentRef.current = '';
      currentDisplayedContentRef.current = '';

      typingIntervalRef.current = setInterval(() => {
        if (currentDisplayedContentRef.current.length < targetContentRef.current.length) {
          const nextChar = targetContentRef.current[currentDisplayedContentRef.current.length];
          currentDisplayedContentRef.current += nextChar;
          
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === assistantMessageId) {
              return [
                ...prev.slice(0, -1),
                { ...lastMessage, content: currentDisplayedContentRef.current }
              ];
            }
            return prev;
          });
        }
      }, 20); // 每 20ms 输出一个字符

      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(value as unknown as Uint8Array, { stream: true });
        fullContent += chunk;

        // 检测分隔符，如果存在则只显示分隔符之前的内容
        const separatorIndex = fullContent.indexOf('<<SUGGESTED_QUESTIONS>>');
        if (separatorIndex !== -1) {
          targetContentRef.current = fullContent.substring(0, separatorIndex);
        } else {
          targetContentRef.current = fullContent;
        }
      }
      
      // 解析后续问题
      const separatorIndex = fullContent.indexOf('<<SUGGESTED_QUESTIONS>>');
      if (separatorIndex !== -1) {
        try {
          // 截取分隔符之后的内容
          const rawStr = fullContent.substring(separatorIndex + '<<SUGGESTED_QUESTIONS>>'.length);
          
          // 使用正则查找 JSON 数组
          const jsonMatch = rawStr.match(/\[[\s\S]*?\]/);
          
          if (jsonMatch) {
            const questions = JSON.parse(jsonMatch[0]);
            if (Array.isArray(questions)) {
              setSuggestedQuestions(questions);
            }
          }
        } catch (e) {
          console.error('Failed to parse suggested questions:', e);
        }
      }

      // 等待打字机效果完成
      while (currentDisplayedContentRef.current.length < targetContentRef.current.length) {
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      setIsLoading(false);
      setIsStreaming(false);
      setShowFollowUp(true);
      if (typingIntervalRef.current) clearInterval(typingIntervalRef.current);
      
    } catch (error) {
      console.error('AI Chat Error:', error);
      if (typingIntervalRef.current) clearInterval(typingIntervalRef.current);
      
      setMessages(prev => {
         const lastMsg = prev[prev.length - 1];
         if (lastMsg.role === 'assistant') {
             return [...prev.slice(0, -1), { ...lastMsg, content: lastMsg.content + '\n\n(连接中断，请重试)' }];
         }
         return [...prev, {
            id: generateMessageId(),
            role: 'assistant',
            content: '抱歉，AI 助手暂时不可用。请稍后再试。',
            timestamp: Date.now(),
         }];
      });
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  // 按 Enter 键发送
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 处理消息内容，支持 <think> 标签的展示
  const processMessageContent = (content: string) => {
    // 替换 <think> 标签为 Markdown 引用块
    return content.replace(/<think>([\s\S]*?)<\/think>/g, (match, thinkContent) => {
      return `> **深度思考**\n>\n> ${thinkContent.trim().split('\n').join('\n> ')}\n\n`;
    });
  };

  return (
    <div className="flex flex-col h-full" style={{ background: 'var(--card-bg)' }}>
      {/* 对话历史区域 */}
      <div className="flex-1 overflow-y-auto p-4" ref={messagesEndRef}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-center">
              <div 
                className="inline-flex items-center justify-center w-16 h-16 mb-4"
                style={{ 
                  background: 'var(--primary-bg)',
                  borderRadius: 'var(--radius-lg)'
                }}
              >
                <svg className="w-8 h-8" style={{ color: 'var(--primary)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
                </svg>
              </div>
              <p className="text-lg font-medium mb-2" style={{ color: 'var(--foreground-title)' }}>开始与 AI 助手对话</p>
              <p className="text-sm" style={{ color: 'var(--foreground-tertiary)' }}>询问关于本章节的问题</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div
                key={message.id}
                className={`flex flex-col ${
                  message.role === 'user' ? 'items-end' : 'items-start'
                }`}
              >
                <div className="text-xs mb-1.5 px-1" style={{ color: 'var(--foreground-tertiary)' }}>
                  {message.role === 'user' ? userName : 'AI 助手'}
                </div>

                <div
                  className="max-w-[90%] px-4 py-3"
                  style={{ 
                    background: message.role === 'user' 
                      ? 'var(--primary)'
                      : 'var(--background-secondary)',
                    color: message.role === 'user' ? '#FFFFFF' : 'var(--foreground)',
                    borderRadius: 'var(--radius-md)',
                    width: message.role === 'assistant' ? '100%' : undefined,
                    maxWidth: message.role === 'assistant' ? '100%' : undefined,
                  }}
                >
                  <div className={`text-sm leading-relaxed ${message.role === 'user' ? 'whitespace-pre-wrap' : ''}`}>
                    {message.role === 'user' ? (
                      message.content
                    ) : message.content ? (
                      <MarkdownReader content={processMessageContent(message.content)} variant="chat" />
                    ) : (
                      <div className="flex items-center space-x-3 py-1">
                        <div className="flex space-x-1">
                          <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--primary)', animationDelay: '0ms' }}></span>
                          <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--primary)', animationDelay: '150ms' }}></span>
                          <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--primary)', animationDelay: '300ms' }}></span>
                        </div>
                        <span style={{ color: 'var(--foreground-secondary)' }}>{thinkingText || '正在思考...'}</span>
                      </div>
                    )}
                  </div>
                  
                  {message.role === 'assistant' && 
                   index === messages.length - 1 && 
                   showFollowUp && (
                    <div className="mt-3 pt-3 flex flex-wrap gap-2" style={{ borderTop: '1px solid var(--card-border)' }}>
                      {suggestedQuestions.map((q, i) => (
                        <button
                          key={i}
                          onClick={() => { setInput(q); handleSendMessage(); }}
                          className="px-3 py-1.5 text-xs transition-colors"
                          style={{ 
                            background: 'var(--card-bg)',
                            color: 'var(--foreground)',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--card-border)',
                          }}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div 
        className="border-t p-4"
        style={{ 
          background: 'var(--background-secondary)',
          borderColor: 'var(--card-border)'
        }}
      >
        {!userId ? (
          <p className="text-sm text-center py-4" style={{ color: 'var(--foreground-tertiary)' }}>
            请先登录以使用 AI 助手
          </p>
        ) : (
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入你的问题..."
              disabled={isLoading}
              className="flex-1 px-4 py-3 focus:outline-none disabled:opacity-50 text-base transition-all"
              style={{ 
                background: 'var(--card-bg)',
                border: '1px solid var(--card-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--foreground)',
              }}
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !input.trim()}
              className="px-5 py-3 font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              style={{ 
                background: 'var(--primary)',
                color: '#FFFFFF',
                borderRadius: 'var(--radius-md)'
              }}
            >
              {isLoading ? (
                <span className="inline-flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8 8 018 16z"></path>
                  </svg>
                  {isStreaming ? '接收中...' : '等待响应...'}
                </span>
              ) : (
                '发送'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
