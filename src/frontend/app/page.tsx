'use client';

import { useEffect, useState } from 'react';
import { useApp } from '@/app/context';

export default function HomePage() {
  const { user, setUser, createUser, logout, loadUser } = useApp();
  const [nickname, setNickname] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadUser();
  }, []);

  useEffect(() => {
    if (user) {
      setNickname(user.nickname || '');
    }
  }, [user]);

  const handleCreateUser = async () => {
    setLoading(true);
    setMessage('');
    try {
      await createUser(nickname || undefined);
      setMessage('用户创建成功！');
      setNickname('');
    } catch (error) {
      setMessage('创建用户失败: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchUser = () => {
    logout();
    setNickname('');
    setMessage('');
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--background)' }}>
        <div 
          className="w-full max-w-md p-8"
          style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--card-border)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <div className="text-center mb-8">
            <div 
              className="w-16 h-16 mx-auto mb-4 flex items-center justify-center"
              style={{ 
                background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground-title)' }}>
              AILearn Hub
            </h1>
            <p style={{ color: 'var(--foreground-secondary)' }}>
              用AI学AI，智能高效学习
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--foreground)' }}>
                昵称（可选）
              </label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                className="w-full px-4 py-3 text-base outline-none transition-all"
                style={{ 
                  color: 'var(--foreground)',
                  borderColor: 'var(--card-border)',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--background)',
                  border: '1px solid var(--card-border)',
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--primary)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'var(--card-border)';
                }}
                placeholder="给自己取个名字吧"
              />
            </div>

            <button
              onClick={handleCreateUser}
              disabled={loading}
              className="w-full py-3 text-white font-medium transition-opacity disabled:opacity-50"
              style={{
                background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              {loading ? '创建中...' : '开始学习之旅'}
            </button>
          </div>

          {message && (
            <div 
              className="mt-4 p-3 text-center text-sm"
              style={{ 
                background: message.includes('成功') ? 'var(--success-light)' : 'var(--error-light)',
                color: message.includes('成功') ? 'var(--success-dark)' : 'var(--error-dark)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              {message}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--background)' }}>
      <nav 
        className="sticky top-0 z-50 border-b"
        style={{ 
          background: 'var(--card-bg)',
          borderColor: 'var(--card-border)',
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-14">
            <div className="flex items-center gap-3">
              <div 
                className="w-9 h-9 flex items-center justify-center"
                style={{ 
                  background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <span className="text-lg font-bold" style={{ color: 'var(--foreground-title)' }}>
                AILearn Hub
              </span>
            </div>
            
            <div className="flex items-center gap-3">
              <span 
                className="hidden sm:block px-3 py-1 text-sm"
                style={{ 
                  background: 'var(--primary-bg)',
                  color: 'var(--primary)',
                  borderRadius: 'var(--radius-full)',
                }}
              >
                {user?.nickname || user?.username}
              </span>
              
              <button
                onClick={handleSwitchUser}
                className="px-3 py-1.5 text-sm"
                style={{ 
                  color: 'var(--foreground-secondary)',
                  background: 'var(--background-secondary)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                切换用户
              </button>
              
              <button
                onClick={logout}
                className="px-3 py-1.5 text-sm"
                style={{ 
                  color: 'var(--error)',
                  background: 'var(--error-light)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                退出
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div 
          className="mb-8 p-6"
          style={{
            background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <h2 className="text-2xl font-bold text-white mb-2">
            你好，{user?.nickname || user?.username}！
          </h2>
          <p className="text-white/90">
            今天想学点什么？选择一个课程开始你的学习之旅吧。
          </p>
        </div>

        <a 
          href="/courses" 
          className="block p-6 group"
          style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--card-border)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold mb-1" style={{ color: 'var(--foreground-title)' }}>
                选择课程
              </h3>
              <p className="text-sm" style={{ color: 'var(--foreground-secondary)' }}>
                选择一个课程开始学习，支持刷题和考试模式
              </p>
            </div>
            <svg 
              className="w-5 h-5 transition-transform group-hover:translate-x-1" 
              style={{ color: 'var(--primary)' }}
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </a>
      </div>
    </div>
  );
}
