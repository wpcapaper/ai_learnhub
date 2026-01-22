'use client';

import { useEffect, useState, Suspense, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiClient, Question, Course } from '@/lib/api';
import LaTeXRenderer from '@/components/LaTeXRenderer';
import Link from 'next/link';

function QuizContent() {
  const [userId, setUserId] = useState<string | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [batch, setBatch] = useState<any>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [selectedOptions, setSelectedOptions] = useState<Set<string>>(new Set());
  const [autoStartAttempted, setAutoStartAttempted] = useState(false);
  const searchParams = useSearchParams();
  const courseId = searchParams.get('course_id');

  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      setUserId(savedUserId);
    }

    if (courseId) {
      apiClient.getCourse(courseId).then(setCourse).catch(console.error);
    }

    // 自动开始批次（使用 savedUserId 而非状态，避免异步更新问题）
    if (savedUserId && courseId && !batch && !autoStartAttempted) {
      setAutoStartAttempted(true);
      startBatchDirect(savedUserId, courseId);
    }
  }, [courseId]);

  const startBatchDirect = async (uid: string, cid: string) => {
    setLoading(true);
    try {
      const batchData = await apiClient.startBatch(uid, 'practice', 10, cid);
      setBatch(batchData);
      const questionsData = await apiClient.getBatchQuestions(uid, batchData.id);
      setQuestions(questionsData);
      setCurrentIndex(0);
      setCompleted(false);
    } catch (error) {
      console.error('Failed to start batch:', error);
      alert('开始批次失败: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const startBatch = useCallback(async () => {
    if (!userId) {
      alert('请先登录');
      window.location.href = '/';
      return;
    }

    if (!courseId) {
      alert('请先选择课程');
      window.location.href = '/courses';
      return;
    }

    await startBatchDirect(userId, courseId);
  }, [userId, courseId]);

  /**
   * 提交单题答案（练习模式）
   *
   * 业务逻辑说明：
   * - 练习模式下，只保存答案，不立即判断对错
   * - 提交成功后更新前端状态，标记该题已作答
   * - 提交过程中禁用按钮，防止重复提交
   * - 失败时提示用户，不阻塞后续操作
   *
   * @param questionId 题目ID
   * @param answer 用户选择的答案
   */
  const submitAnswer = async (questionId: string, answer: string) => {
    if (!userId || !batch) return;

    setSubmitting(true);
    try {
      // 调用 API 提交答案（user_id 作为查询参数传递）
      await apiClient.submitBatchAnswer(userId, batch.id, questionId, answer);

      // 更新前端状态，标记该题已作答（不判断对错）
      setQuestions(prev => prev.map(q =>
        q.id === questionId ? { ...q, user_answer: answer } : q
      ));
    } catch (error) {
      console.error('Failed to submit answer:', error);
      alert('提交答案失败');
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * 切换多选题选项选择
   *
   * 业务逻辑说明：
   * - 支持选项选择后可修改：如果题目已回答，从user_answer初始化selectedOptions
   * - 切换选项状态：已选则移除，未选则添加
   * - 更新前端状态，为提交答案做准备
   *
   * @param optionKey 选项键名（如A、B、C等）
   */
  const toggleOption = (optionKey: string) => {
    // 如果题目已回答且selectedOptions为空，从user_answer初始化
    const userAnswer = currentQuestion?.user_answer;
    if (userAnswer != null && selectedOptions.size === 0) {
      const existingOptions = userAnswer.split(',');
      setSelectedOptions(new Set(existingOptions));
      return;
    }

    const newSelected = new Set(selectedOptions);
    if (newSelected.has(optionKey)) {
      newSelected.delete(optionKey);
    } else {
      newSelected.add(optionKey);
    }
    setSelectedOptions(newSelected);
  };

  const submitMultipleChoiceAnswer = async () => {
    if (!currentQuestion) return;

    const sortedOptions = Array.from(selectedOptions).sort();
    const answer = sortedOptions.join(',');

    if (answer.length === 0) {
      alert('请至少选择一个选项');
      return;
    }

    await submitAnswer(currentQuestion.id, answer);
    setSelectedOptions(new Set());
  };

  const finishBatch = async () => {
    if (!userId || !batch) return;

    if (confirm('确认完成批次并查看答案？')) {
      try {
        const result = await apiClient.finishBatch(userId, batch.id);
        setCompleted(true);

        const updatedQuestions = await apiClient.getBatchQuestions(userId, batch.id);
        setQuestions(updatedQuestions);
      } catch (error) {
        console.error('Failed to finish batch:', error);
        alert('完成批次失败');
      }
    }
  };

  const currentQuestion = questions[currentIndex];
  const allAnswered = questions.every(q => q.user_answer !== null);
  const canSubmit = currentQuestion?.user_answer !== null;

  useEffect(() => {
    setSelectedOptions(new Set());
  }, [currentIndex]);

  if (!userId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">请先登录</h1>
            <button
              onClick={() => window.location.href = '/courses'}
              className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
            >
              返回课程
            </button>
        </div>
      </div>
    );
  }

  if (completed) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h1 className="text-2xl font-bold mb-4 text-black">批次完成</h1>
            <div className="text-lg mb-4 text-black">
              <p>总题数: {questions.length}</p>
              <p>已完成: {questions.filter(q => q.user_answer != null).length}</p>
              <p>正确率: {questions.length > 0 ? Math.round((questions.filter(q => q.is_correct === true).length / questions.length) * 100) : 0}%</p>
              <p>做对: {questions.filter(q => q.is_correct === true).length} 题</p>
              <p>做错: {questions.filter(q => q.is_correct === false).length} 题</p>
            </div>
            <button
              onClick={() => {
                window.location.href = '/courses';
                setBatch(null);
                setQuestions([]);
                setCurrentIndex(0);
                setCompleted(false);
              }}
              className="w-full bg-blue-600 text-white py-3 rounded-md hover:bg-blue-700"
            >
              返回课程
            </button>
          </div>

          <div className="space-y-4">
            {questions.map((q, index) => (
              <div key={q.id} className={`bg-white rounded-lg shadow p-6 ${q.is_correct === true ? 'border-l-4 border-green-500' : q.is_correct === false ? 'border-l-4 border-red-500' : ''}`}>
                  <div className="mb-4">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      {/* 完成后也保持题型tag的颜色区分 */}
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        q.question_type === 'single_choice' ? 'bg-blue-100 text-blue-700' :
                        q.question_type === 'multiple_choice' ? 'bg-orange-500 text-white font-bold' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {q.question_type === 'single_choice' ? '单选题' :
                         q.question_type === 'multiple_choice' ? '多选题' : '判断题'}
                      </span>
                      {/* 显示题集来源（仅在批次完成后显示） */}
                      {completed && q.question_set_codes && q.question_set_codes.length > 0 && (
                        <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-700">
                          📚 固定题库: {q.question_set_codes.join(', ')}
                        </span>
                      )}
                    </div>
                    <p className="font-medium mb-2 text-black">{index + 1}. <LaTeXRenderer content={q.content} /></p>
                  {completed && q.question_type === 'multiple_choice' && q.user_answer != null && (
                    <div className="mb-3 p-2 bg-blue-50 rounded text-sm">
                      <span className="font-semibold">你的选项：{q.user_answer}</span>
                      <span className="mx-2">|</span>
                      <span className="font-semibold">正确答案：{q.correct_answer}</span>
                    </div>
                  )}
                  {q.options && (
                    <div className="space-y-2 ml-4">
                      {Object.entries(q.options).map(([key, value]) => {
                        const userAnswer = q.user_answer;
                        const correctAnswer = q.correct_answer;
                        const isUserAnswer = userAnswer != null && userAnswer.includes(key);
                        const isCorrectAnswer = correctAnswer != null && correctAnswer.includes(key);
                        return (
                          <div key={key} className={`p-3 border rounded ${isUserAnswer ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                            <strong className="text-black">{key}.</strong>{' '}
                            <span className="text-black"><LaTeXRenderer content={value} /></span>
                            {completed && isCorrectAnswer && (
                              <span className="ml-2 text-black font-bold">✓ 正确</span>
                            )}
                            {completed && isUserAnswer && !isCorrectAnswer && (
                              <span className="ml-2 text-black font-bold">✗ 错误</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {q.explanation && completed && (
                    <div className="mt-4 p-4 bg-gray-50 rounded border border-gray-200">
                      <strong className="text-black">解析:</strong>
                      <p className="text-black mt-2"><LaTeXRenderer content={q.explanation} /></p>
                    </div>
                  )}
                </div>
              </div>
            ))}
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
              <Link href="/" className="text-2xl font-bold text-gray-800 hover:text-gray-900">
                AILearn Hub
              </Link>
              <span className="ml-4 text-gray-400">/</span>
              {course && (
                <>
                  <Link href="/courses" className="ml-4 text-2xl font-bold text-gray-800 hover:text-gray-900">
                    {course.title}
                  </Link>
                  <span className="ml-4 text-gray-400">/</span>
                  <span className="ml-4 text-2xl font-bold text-gray-800">
                    批次刷题
                  </span>
                </>
              )}
              {!course && (
                <span className="ml-4 text-2xl font-bold text-gray-800">
                  批次刷题
                </span>
              )}
            </div>
              <button
                onClick={() => window.location.href = '/courses'}
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                返回课程
              </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {batch && currentQuestion && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-lg shadow-md p-6 mb-4">
              <div className="mb-4">
                <span className="text-red-600 font-semibold">进度:</span>
                <span className="font-bold ml-2 text-red-600">{currentIndex + 1} / {questions.length}</span>
              </div>

              <div className="mb-6">
                <div className="flex items-center gap-2 mb-2">
                  {/* 调整tag颜色以区分题型，多选题使用醒目颜色 */}
                  <span className={`px-2 py-1 text-xs font-medium rounded ${
                    currentQuestion.question_type === 'single_choice' ? 'bg-blue-100 text-blue-700' :
                    currentQuestion.question_type === 'multiple_choice' ? 'bg-orange-500 text-white font-bold' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {currentQuestion.question_type === 'single_choice' ? '单选题' :
                     currentQuestion.question_type === 'multiple_choice' ? '多选题' : '判断题'}
                  </span>
                  {/* 刷题模式中显示题目来源 - 在答题过程中也能看到 */}
                  {currentQuestion.question_set_codes && currentQuestion.question_set_codes.length > 0 && (
                    <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-700">
                      📚 {currentQuestion.question_set_codes.join(', ')}
                    </span>
                  )}
                </div>
                <h2 className="text-xl font-bold mb-4 text-gray-900">
                  <LaTeXRenderer content={currentQuestion.content} />
                </h2>
                {currentQuestion.options && (
                  <div className="space-y-3">
                    {currentQuestion.question_type === 'multiple_choice' ? (
                      Object.entries(currentQuestion.options).map(([key, value]) => {
                        const isSelected = selectedOptions.has(key);
                        const userAnswer = currentQuestion.user_answer;
                        const isAlreadyAnswered = userAnswer != null;
                        const isOptionSelected = isAlreadyAnswered && userAnswer.includes(key);

                        return (
                        <button
                          key={key}
                          onClick={() => toggleOption(key)}
                          disabled={submitting}
                          className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                            isSelected || isOptionSelected
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          <strong className="text-lg text-blue-600">{key}.</strong>{' '}
                          <span className="text-gray-900"><LaTeXRenderer content={value} /></span>
                          {(isSelected || isOptionSelected) && (
                            <span className="ml-2 text-blue-600 font-bold">✓ 已选择</span>
                          )}
                        </button>
                        );
                      })
                    ) : (
                      Object.entries(currentQuestion.options).map(([key, value]) => (
                        <button
                          key={key}
                          onClick={() => submitAnswer(currentQuestion.id, key)}
                          disabled={submitting}
                          className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                            currentQuestion.user_answer === key
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          <strong className="text-lg text-blue-600">{key}.</strong>{' '}
                          <span className="text-gray-900"><LaTeXRenderer content={value} /></span>
                          {currentQuestion.user_answer === key && (
                            <span className="ml-2 text-blue-600 font-bold">✓ 已选择</span>
                          )}
                        </button>
                      ))
                    )}
                  </div>
                )}

              {/* 允许用户在答题过程中修改多选题答案 */}
              {currentQuestion.question_type === 'multiple_choice' && selectedOptions.size > 0 && (
                <button
                  onClick={submitMultipleChoiceAnswer}
                  disabled={submitting || selectedOptions.size === 0}
                  className="w-full mt-4 bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? '提交中...' : '提交答案'}
                </button>
              )}
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
                  disabled={currentIndex === 0 || submitting}
                  className="flex-1 bg-gray-200 text-gray-700 py-3 rounded-lg hover:bg-gray-300 disabled:opacity-50"
                >
                  上一题
                </button>
                <button
                  onClick={() => setCurrentIndex(Math.min(questions.length - 1, currentIndex + 1))}
                  disabled={currentIndex === questions.length - 1 || submitting}
                  className="flex-1 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {currentIndex === questions.length - 1 ? '查看答案' : '下一题'}
                </button>
              </div>

              {currentIndex === questions.length - 1 && allAnswered && (
                <button
                  onClick={finishBatch}
                  disabled={completed}
                  className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 mt-4"
                >
                  {completed ? '已完成' : '完成批次'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function QuizPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-gray-50">加载中...</div>}>
      <QuizContent />
    </Suspense>
  );
}
