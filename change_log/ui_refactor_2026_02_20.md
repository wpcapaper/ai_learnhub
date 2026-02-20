# UI重构变更日志

## 变更日期
2026-02-20

## 变更类型
用户端UI整体重构 + Docker构建配置统一

## 变更摘要
1. **UI重构**：采用 Magic UI 组件库进行现代化设计，支持4种主题切换，使用 Particles、MagicCard、BorderBeam、NumberTicker 等组件打造现代科技感界面。
2. **Docker配置**：统一 frontend 与 admin-frontend 的 Docker 构建配置，解决长期存在的依赖缓存问题。

---

## 一、UI重构变更详情

### 1. 全局样式系统 (globals.css)
**变更前问题：**
- 单一配色方案，用户无法根据喜好选择
- 配色饱和度过低（莫兰迪色系），页面显得"褪色"

**改进内容：**
- 新增4种主题配色方案：
  - `modern-tech`（现代科技风，默认）：科技蓝绿 #0EA5E9
  - `fresh-nature`（清新自然）：清新绿 #22C55E
  - `warm-sunshine`（暖阳橙）：温暖橙 #F59E0B
  - `scholarly-blue`（学者蓝）：沉稳蓝 #3B82F6
- 提高颜色饱和度，视觉更加鲜活
- 优化 Markdown 代码块样式，支持语法高亮

### 2. 新增 Magic UI 组件
| 组件 | 用途 | 应用页面 |
|------|------|----------|
| `Particles` | 粒子动画背景 | 所有页面 |
| `MagicCard` | 发光悬停效果的卡片 | 首页、课程、章节、统计 |
| `BorderBeam` | 边框光束动画 | 首页登录卡片 |
| `NumberTicker` | 数字滚动动画 | 统计页、错题本 |
| `ShimmerButton` | 微光按钮 | 首页登录按钮 |
| `ThemeSelector` | 主题切换器 | 所有页面导航栏 |

### 3. 首页 (page.tsx)
**改进内容：**
- Particles 粒子背景动画
- MagicCard 替换普通卡片
- BorderBeam 边框光束效果
- ShimmerButton 登录按钮
- 渐变色标题和图标
- ThemeSelector 主题切换

### 4. 课程页 (courses/page.tsx)
**改进内容：**
- Particles 背景效果
- MagicCard 课程卡片
- 渐变色进度条
- 主题色按钮和标签

### 5. 学习页 (learning/page.tsx)
**改进内容：**
- 减少左右边距（px-4 → px-2），内容区更宽
- Particles 背景效果
- 渐变色进度条
- 现代化导航栏

### 6. 统计页 (stats/page.tsx)
**改进内容：**
- NumberTicker 数字滚动动画
- MagicCard 统计卡片
- Particles 背景效果
- 渐变色进度可视化

### 7. 刷题页/考试页 (quiz/page.tsx, exam/page.tsx)
**改进内容：**
- Particles 背景效果
- MagicCard 题目卡片（根据对错显示不同渐变色）
- 主题色选项样式
- 渐变色按钮和进度条

### 8. 错题本页 (mistakes/page.tsx)
**改进内容：**
- Particles 背景效果
- NumberTicker 统计数字动画
- MagicCard 错题卡片
- 渐变色重练按钮

### 9. 章节页 (chapters/page.tsx)
**改进内容：**
- Particles 背景效果
- MagicCard 章节卡片
- 渐变色序号图标
- 进度条可视化

### 10. 上下文和主题管理 (context.tsx)
**新增内容：**
- `theme` 状态管理
- `setTheme()` 切换函数
- localStorage 持久化主题设置

---

## 二、Docker构建配置变更

### 问题背景
**长期存在的问题：**
1. `frontend` 服务使用 `image: node:20-alpine` + `command` 模式
2. `admin-frontend` 服务使用 `build: Dockerfile` 模式
3. 两者构建方式不一致，导致 `docker-compose build` 只构建 admin-frontend
4. frontend 依赖更新后（如新增 clsx、tailwind-merge、motion），Docker 容器中的匿名卷缓存旧依赖，导致构建失败
5. 每次需要手动执行 `docker-compose down -v` 清除匿名卷才能解决

**错误表现：**
```
Module not found: Can't resolve 'clsx'
./lib/utils.ts (1:1)
```

### 解决方案
**1. 统一 Dockerfile 结构 (src/frontend/Dockerfile)**

将 frontend 的 Dockerfile 改为与 admin-frontend 相同的多阶段构建模式：

```dockerfile
# 多阶段构建：deps → builder → runner
FROM node:20-alpine AS deps
# 安装依赖...

FROM node:20-alpine AS builder  
# 构建应用...

FROM node:20-alpine AS runner
# 生产运行...
```

**2. 统一 docker-compose.yml 配置**

变更前：
```yaml
frontend:
  image: node:20-alpine  # 使用镜像
  command: sh -c "npm install && npm run dev"  # 开发模式
  volumes:
    - ./src/frontend:/app
    - /app/node_modules  # 匿名卷，容易缓存问题
```

变更后：
```yaml
frontend:
  build:
    context: ./src/frontend
    dockerfile: Dockerfile
    args:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT:-8000}
  image: ailearn-frontend:latest
  environment:
    - NODE_ENV=production
```

### 解决的问题
1. ✅ `docker-compose build` 现在会同时构建 frontend 和 admin-frontend
2. ✅ 不再有匿名卷缓存问题，每次构建都会安装最新依赖
3. ✅ 两个前端服务配置风格统一，易于维护
4. ✅ 生产模式运行，性能更好
5. ✅ 非 root 用户运行，安全性更高

### 注意事项
- 现在 frontend 也是生产模式（build + standalone），不再支持热重载
- 本地开发建议直接运行 `npm run dev`，Docker 用于生产部署

---

## 三、文件变更列表

### UI 重构文件
| 文件路径 | 变更类型 |
|---------|---------|
| src/frontend/app/globals.css | 修改（4主题系统） |
| src/frontend/app/context.tsx | 修改（主题管理） |
| src/frontend/app/page.tsx | 修改（Magic UI） |
| src/frontend/app/courses/page.tsx | 修改（Magic UI） |
| src/frontend/app/learning/page.tsx | 修改（Magic UI + 边距） |
| src/frontend/app/stats/page.tsx | 修改（NumberTicker） |
| src/frontend/app/quiz/page.tsx | 修改（Magic UI） |
| src/frontend/app/exam/page.tsx | 修改（Magic UI） |
| src/frontend/app/mistakes/page.tsx | 修改（Magic UI） |
| src/frontend/app/chapters/page.tsx | 修改（Magic UI） |
| src/frontend/components/ThemeSelector.tsx | 新增 |
| src/frontend/components/ui/particles.tsx | 新增 |
| src/frontend/components/ui/magic-card.tsx | 新增 |
| src/frontend/components/ui/border-beam.tsx | 新增 |
| src/frontend/components/ui/number-ticker.tsx | 新增 |
| src/frontend/components/ui/shimmer-button.tsx | 新增 |
| src/frontend/components/ui/animated-list.tsx | 新增 |
| src/frontend/components/ui/animated-gradient-text.tsx | 新增 |
| src/frontend/lib/utils.ts | 新增 |
| src/frontend/components.json | 新增 |

### Docker 配置文件
| 文件路径 | 变更类型 |
|---------|---------|
| src/frontend/Dockerfile | 修改（多阶段构建） |
| docker-compose.yml | 修改（frontend 改为 build 模式） |

---

## 四、影响评估

### 正面影响
1. **视觉效果提升**：现代科技感设计，动画效果丰富
2. **用户个性化**：4种主题可选，满足不同喜好
3. **维护性提升**：Docker 配置统一，不再有缓存问题
4. **安全性提升**：非 root 用户运行，多阶段构建减小攻击面

### 潜在风险
1. 动画效果可能在低端设备上影响性能
2. 生产模式不支持热重载，本地开发需直接运行 npm 命令

## 测试建议
1. 测试所有4种主题的视觉效果
2. 测试主题切换后页面刷新是否保持
3. 运行 `docker-compose build --no-cache` 验证构建正常
4. 验证所有页面功能正常运行
