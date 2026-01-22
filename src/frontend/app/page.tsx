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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full mx-auto p-6">
          <div className="bg-white rounded-lg shadow-md p-8">
            <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">
              AILearn Hub
            </h1>
            <p className="text-center text-gray-700 mb-8">
              欢迎来到AI学习系统 - 用AI学AI
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-800 mb-2">
                  昵称（可选）
                </label>
                <input
                  type="text"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  className="w-full px-3 py-2 text-gray-900 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  placeholder="输入昵称"
                />
              </div>

              <button
                onClick={handleCreateUser}
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md py-2.5 px-4 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '创建中...' : '开始学习'}
              </button>
            </div>

            {message && (
              <div className={`mt-4 p-4 rounded-md ${message.includes('成功') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {message}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-800">
                AILearn Hub
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                {user?.nickname || user?.username}
              </span>
              <button
                onClick={handleSwitchUser}
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                切换用户
              </button>
              <button
                onClick={logout}
                className="text-red-600 hover:text-red-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                退出登录
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <h2 className="text-xl font-bold text-gray-800 mb-4">
              选择课程
            </h2>
            <p className="text-gray-700 mb-4">
              选择一个课程开始学习，支持刷题和考试模式
            </p>
            <a
              href="/courses"
              className="block w-full bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md py-2.5 px-4 text-center transition-colors"
            >
              查看课程
            </a>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <h2 className="text-xl font-bold text-gray-800 mb-4">
              学习统计
            </h2>
            <p className="text-gray-700 mb-4">
              查看你的学习进度、正确率和已掌握题目
            </p>
            <a
              href="/stats"
              className="block w-full bg-green-600 hover:bg-green-700 text-white font-medium rounded-md py-2.5 px-4 text-center transition-colors"
            >
              查看统计
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
