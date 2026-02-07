'use client';

import { useEffect, useState } from 'react';
import { apiClient, User } from '@/lib/api';

export default function StatsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [userStats, setUserStats] = useState<any>(null);
  const [reviewStats, setReviewStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadUser = async () => {
      const savedUserId = localStorage.getItem('userId');
      if (savedUserId) {
        const userData = await apiClient.getUser(savedUserId);
        setUser(userData);
        loadStats(savedUserId);
      }
    };

    loadUser();
  }, []);

  const loadStats = async (uid: string) => {
    setLoading(true);
    try {
      const [userStatsData, reviewStatsData] = await Promise.all([
        apiClient.getUserStats(uid),
        apiClient.getReviewStats(uid),
      ]);
      setUserStats(userStatsData);
      setReviewStats(reviewStatsData);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('userId');
    setUser(null);
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">请先登录</h1>
          <button
            onClick={() => window.location.href = '/'}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
          >
            返回首页
          </button>
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
                学习统计
              </h1>
            </div>
            <button
              onClick={handleLogout}
              className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
            >
              切换用户
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-4 text-gray-700">加载中...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-4">学习概况</h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-4 bg-blue-50 rounded-lg">
                  <div>
                    <p className="text-sm text-gray-700">总答题数</p>
                    <p className="text-3xl font-bold text-gray-800">{userStats?.total_answered || 0}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-700">正确数</p>
                    <p className="text-3xl font-bold text-green-600">{userStats?.correct_count || 0}</p>
                  </div>
                </div>

                <div className="p-4 bg-green-50 rounded-lg">
                  <div className="text-center">
                    <p className="text-sm text-gray-700">正确率</p>
                    <p className="text-4xl font-bold text-green-700">{userStats?.accuracy || 0}%</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center p-4 bg-purple-50 rounded-lg">
                    <p className="text-sm text-gray-700">已掌握</p>
                    <p className="text-2xl font-bold text-purple-700">{userStats?.mastered_count || 0}</p>
                  </div>
                  <div className="flex items-center p-4 bg-yellow-50 rounded-lg">
                    <p className="text-sm text-gray-700">待复习</p>
                    <p className="text-2xl font-bold text-yellow-700">{reviewStats?.due_count || 0}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-4">艾宾浩斯复习</h2>
              <div className="space-y-4">
                <div className="text-center p-6 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg">
                  <p className="text-white text-lg font-bold">待复习题目</p>
                  <p className="text-white text-5xl font-bold mt-2">{reviewStats?.due_count || 0}</p>
                </div>

                <div className="text-center p-6 bg-green-100 rounded-lg">
                  <p className="text-gray-800 text-lg font-bold">已掌握题目</p>
                  <p className="text-green-700 text-5xl font-bold mt-2">{userStats?.mastered_count || 0}</p>
                </div>

                <div className="text-sm text-gray-700 p-4">
                  <p>艾宾浩斯记忆曲线帮助你高效复习：</p>
                  <ul className="list-disc list-inside mt-2 space-y-2">
                    <li>优先复习错题和新题</li>
                    <li>按30分钟、12小时、1天、2天、4天、7天、15天间隔复习</li>
                    <li>答对升级复习阶段，答错回到第一阶段</li>
                    <li>达到第8阶段为已掌握</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
