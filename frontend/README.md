# 管理后台前端

基于 Vue 3 + TypeScript + Element Plus 构建的管理后台前端。

## 特性

- Vue 3 + TypeScript
- Element Plus UI 组件库
- Vue Router 4
- Pinia 状态管理
- Axios HTTP 客户端
- 响应式设计
- 路由权限控制
- 登录/注册页面
- 仪表板页面

## 快速开始

安装依赖：
pnpm install

开发环境：
pnpm dev

应用将在本地3000端口启动。

构建生产版本：
pnpm build

预览生产版本：
pnpm preview

## 项目结构

frontend/
├── src/
│   ├── api/           API 接口封装
│   ├── assets/        静态资源
│   ├── components/    公共组件
│   ├── router/        路由配置
│   ├── stores/        Pinia 状态管理
│   ├── styles/        样式文件
│   ├── views/         页面组件
│   ├── App.vue        根组件
│   └── main.ts        应用入口
├── index.html         HTML 模板
└── vite.config.ts     Vite 配置

## 页面说明

登录页面：
- 支持用户名或邮箱登录
- 无验证码，简化登录流程
- 表单验证

注册页面：
- 用户名、邮箱、姓名、密码注册
- 密码确认验证
- 注册成功后跳转登录

仪表板：
- 欢迎信息和用户信息展示
- 统计数据卡片
- 侧边栏导航
- 用户菜单（退出登录）

## API 配置

前端默认代理 /api/v1 请求到后端服务，可在 vite.config.ts 中修改。

## 后端接口要求

登录接口：
POST /api/v1/auth/login
Content-Type: application/json

注册接口：
POST /api/v1/auth/register
Content-Type: application/json

用户信息接口：
GET /api/v1/auth/user
Authorization: Bearer {token}

## 技术栈

- Vue 3
- TypeScript
- Element Plus
- Vite
- Pinia
- Vue Router
- Axios

## 许可证

MIT
