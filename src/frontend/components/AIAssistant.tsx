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
    <div className="flex flex-col h-full bg-white">
      {/* 对话历史区域 */}
      <div className="flex-1 overflow-y-auto p-4" ref={messagesEndRef}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-50 rounded-full mb-4">
                <svg className="w-8 h-8 text-indigo-600" fill="none" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12 2c5.52 0 10 4.48 10 10v2c0 2-1.58-.72-3.28-2-3.28V6c0-2.72 2.48-2 72-6.28 2-3.28C20.72 2 22 6.48 22 12s0-5.52-4.48-10-10zm0 12c1.1 0 2 .9 2 2s-2.2V8c0-1.1-.9-2-2-.9-2h-1.1v2h2v-2h2c1.1 0 2 .9 2 2s0 .9 2 2h4.2l-3.8-2.1-1.6-1.6V10c0-3.6.4-6.3-1.5-7l-2.8-2.3-1.6-2.6-.5-3.1.6-4.5.8-3.2-6.3-2.9-4.3-8.3-1.5-1.2-.5-2.1-4.2-1.5-6.4-3.7-9.6-5.2-6.9-2.1-3.6-5.1-8.3-6.5-9.1-1.6-4.9-4.4-5.4-5.3-8.5-5-8-9.4-1.1-3.6-8.2-9.9-9.2-10.9-10.8-12.7z"></path>
                </svg>
              </div>
              <p className="text-lg text-slate-700 font-medium mb-2">开始与 AI 助手对话</p>
              <p className="text-sm text-slate-500">询问关于本章节的问题</p>
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
                {/* 显示名称 */}
                <div className="text-xs text-slate-500 mb-2">
                  {message.role === 'user' ? userName : 'AI 助手'}
                </div>

                {/* 消息气泡 */}
                <div
                  className={`max-w-[90%] shadow-lg px-5 py-3 ${
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-br-2xl'
                      : 'bg-white border border-slate-100 text-slate-800 rounded-bl-2xl w-full'
                  }`}
                >
                  <div className={`text-sm leading-relaxed ${message.role === 'user' ? 'whitespace-pre-wrap' : ''}`}>
                    {message.role === 'user' ? (
                      message.content
                    ) : (
                      <MarkdownReader content={processMessageContent(message.content)} variant="chat" />
                    )}
                  </div>
                  
                  {/* 后续问题推荐 (仅在最后一条 AI 消息后显示) */}
                  {message.role === 'assistant' && 
                   index === messages.length - 1 && 
                   showFollowUp && (
                    <div className="mt-4 flex flex-wrap gap-2 animate-fade-in">
                      {suggestedQuestions.map((q, i) => (
                        <button
                          key={i}
                          onClick={() => { setInput(q); handleSendMessage(); }}
                          className="px-3 py-1.5 bg-indigo-50 text-indigo-700 text-xs rounded-full border border-indigo-100 hover:bg-indigo-100 hover:border-indigo-200 transition-colors"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {/* 思考状态展示 */}
            {isLoading && !isStreaming && (
               <div className="flex flex-col items-start">
                  <div className="text-xs text-slate-500 mb-2">AI 助手</div>
                  <div className="bg-slate-50 border border-slate-100 text-slate-500 rounded-bl-2xl rounded-tr-2xl rounded-tl-2xl px-5 py-3 shadow-sm">
                    <div className="flex items-center space-x-2">
                       <svg className="animate-spin h-4 w-4 text-indigo-500" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8 8 018 16z"></path>
                       </svg>
                       <span className="text-sm animate-pulse">{thinkingText}</span>
                    </div>
                  </div>
               </div>
            )}
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="border-t border-slate-200 p-4 bg-slate-50">
        {!userId ? (
          <p className="text-sm text-slate-500 text-center py-4">
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
              className="flex-1 px-4 py-3 bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-slate-100 disabled:text-slate-400 text-base transition-all"
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-xl hover:from-indigo-700 hover:to-indigo-800 disabled:from-slate-400 disabled:to-slate-400 disabled:cursor-not-allowed transition-all shadow-md text-sm font-medium"
            >
              {isStreaming ? (
                <span className="inline-flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8 8 018 16z"></path>
                  </svg>
                  发送中...
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
