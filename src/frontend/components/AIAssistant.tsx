'use client';

import { useState, useRef, useEffect } from 'react';
import { apiClient } from '@/lib/api';

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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const userName = '我';

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
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setIsStreaming(true);

    try {
      // 调用 AI 对话接口（流式响应）
      const stream = await apiClient.aiChatStream(chapterId, input, userId);
      const reader = stream.getReader();
      const decoder = new TextDecoder();

      let assistantMessage = '';
      const assistantMessageId = Date.now().toString();

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        assistantMessage += decoder.decode(value as unknown as Uint8Array, { stream: true });

        // 更新 AI 助手消息
        setMessages(prev => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === assistantMessageId) {
            // 更新现有消息
            return [
              ...prev.slice(0, -1),
              { ...lastMessage, content: assistantMessage }
            ];
          } else {
            // 添加新消息
            return [
              ...prev,
              {
                id: assistantMessageId,
                role: 'assistant',
                content: assistantMessage,
                timestamp: Date.now(),
              }
            ];
          }
        });
      }

      setIsLoading(false);
      setIsStreaming(false);
    } catch (error) {
      console.error('AI Chat Error:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: '抱歉，AI 助手暂时不可用。请稍后再试。',
        timestamp: Date.now(),
      }]);
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
            {messages.map((message) => (
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
                  className={`max-w-[80%] shadow-lg px-5 py-3 ${
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-br-2xl'
                      : 'bg-slate-100 text-slate-800 rounded-bl-2xl'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    {message.content}
                  </div>
                </div>
              </div>
            ))}
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
