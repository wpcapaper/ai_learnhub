import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AILearn Hub - Admin",
  description: "管理后台 - RAG优化、课程管理、系统配置",
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
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="min-h-screen">
        <div className="flex h-screen">
          {/* ========== 侧边栏 ========== */}
          <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar-logo">
              <a href="/" className="flex items-center gap-3 group">
                <div className="relative">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#8b5cf6] to-[#06b6d4] flex items-center justify-center shadow-lg shadow-[#8b5cf6]/20">
                    <svg style={{width: '18px', height: '18px'}} fill="none" stroke="white" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <div className="absolute -inset-1 rounded-xl bg-gradient-to-br from-[#8b5cf6]/30 to-[#06b6d4]/30 blur opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div>
                  <span className="block text-[15px] font-semibold gradient-text">AILearn</span>
                  <span className="block text-[10px] text-[#71717a] tracking-wide">Admin Console</span>
                </div>
              </a>
            </div>
            
            {/* 导航 */}
            <nav className="sidebar-nav">
              <div className="mb-3 px-3">
                <span className="text-[10px] font-medium text-[#52525b] uppercase tracking-wider">主菜单</span>
              </div>
              <div className="space-y-0.5">
                <NavItem href="/" icon="courses" label="课程管理" active />
                <NavItem href="/optimization" icon="optimize" label="RAG 优化" />
                <NavItem href="/evaluation" icon="chart" label="质量评估" />
              </div>
              
              <div className="mt-6 mb-3 px-3">
                <span className="text-[10px] font-medium text-[#52525b] uppercase tracking-wider">系统</span>
              </div>
              <div className="space-y-0.5">
                <NavItem href="/settings" icon="settings" label="系统设置" />
              </div>
            </nav>
            
            {/* 底部状态 */}
            <div className="p-4 border-t border-[rgba(255,255,255,0.06)]">
              <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[rgba(139,92,246,0.08)]">
                <div className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-[#fafafa]">系统运行中</div>
                  <div className="text-[10px] text-[#71717a]">v2.0.0</div>
                </div>
              </div>
            </div>
          </aside>
          
          {/* 主内容区 */}
          <main className="flex-1 overflow-auto dot-bg">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

function NavItem({ href, icon, label, active = false }: { href: string; icon: string; label: string; active?: boolean }) {
  const iconPaths: Record<string, string> = {
    courses: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
    optimize: "M13 10V3L4 14h7v7l9-11h-7z",
    settings: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z",
    chart: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  };

  return (
    <a
      href={href}
      className={`sidebar-item ${active ? 'active' : ''}`}
    >
      <svg style={{width: '18px', height: '18px', minWidth: '18px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
        <path d={iconPaths[icon]} />
      </svg>
      <span>{label}</span>
    </a>
  );
}
