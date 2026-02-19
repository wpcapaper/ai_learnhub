import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AILearn Hub - Admin",
  description: "管理后台 - RAG测试、课程管理、系统配置",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <head>
        <link 
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <nav className="border-b border-gray-800 bg-gray-900">
          <div className="max-w-7xl mx-auto px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-8">
                <a href="/" className="text-xl font-bold text-green-400 font-mono">
                  &gt;_ AILearn Admin
                </a>
                <div className="flex space-x-4">
                  <a 
                    href="/" 
                    className="text-gray-400 hover:text-green-400 transition-colors font-mono text-sm"
                  >
                    [课程管理]
                  </a>
                  <a 
                    href="/rag-test" 
                    className="text-gray-400 hover:text-green-400 transition-colors font-mono text-sm"
                  >
                    [RAG测试]
                  </a>
                  <a 
                    href="/rag-expert" 
                    className="text-gray-400 hover:text-cyan-400 transition-colors font-mono text-sm"
                  >
                    [RAG专家]
                  </a>
                  <a 
                    href="/optimization" 
                    className="text-gray-400 hover:text-yellow-400 transition-colors font-mono text-sm"
                  >
                    [分块优化]
                  </a>
                </div>
              </div>
              <div className="text-gray-500 text-sm font-mono">
                v1.0.0 | 管理端
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
