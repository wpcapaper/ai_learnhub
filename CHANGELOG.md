# Changelog

All notable changes to this project will be documented in this file.

## [code_block_theme_fix_20260222] - 2026-02-22

### Fixed
- 代码块语法高亮符号类出现不当背景色的问题
- 代码块不适配前端主题配色（浅色主题下使用深色背景）
- 代码块黑色外边框问题

### Changed
- 浅色主题代码块背景改为浅灰色 (#f6f8fa)
- 新增语法高亮 token 颜色 CSS 变量（浅色/深色各 12 个）
- 移除代码块边框，使用圆角设计
- MarkdownReader 组件使用自定义语法高亮样式

### Files
- `src/frontend/app/globals.css`
- `src/frontend/components/MarkdownReader.tsx`

详见：`~/Codes/vibe-coding-logs/change_log/aie55_llm5_learnhub/code_block_theme_fix_20260222.md`
