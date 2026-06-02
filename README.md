# 🎨 AI 手办多模态设计平台

> **让每个人都能设计自己的 3D 手办**
>
> An AI-powered platform that transforms your ideas into 3D figures through multimodal generation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

---

## ✨ 项目亮点

🎯 **一站式设计流程** — 从灵感素材到 2D 图像再到 3D 模型，完整创作链路

🎨 **多风格支持** — Q版手办、写实、赛博朋克、水墨等多种风格模板

🎲 **智能抽卡** — 不满意可重新生成，满意即可收入素材库

🔄 **2D → 3D 重建** — 基于 Doubao-Seed3D-2.0，自动将 2D 图像转为 3D 模型

👁️ **实时 3D 预览** — Three.js 渲染，支持旋转、缩放、多角度查看

---

## 🎬 演示

<!-- 请将截图放在 static/images/ 目录下，并替换以下链接 -->

| 功能 | 预览 |
|------|------|
| 2D 图像生成 | ![2D Generation](static/images/placeholder.svg) |
| 3D 模型预览 | ![3D Preview](static/images/placeholder.svg) |
| 后台管理 | ![Admin Panel](static/images/placeholder.svg) |

> 💡 **提示**：运行项目后访问 http://127.0.0.1:5000 体验完整功能

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 火山引擎 API Key（用于 AI 生成服务）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/Jasonlieee/AI_3D_Platform_Demo.git
cd AI_3D_Platform_Demo

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python app.py
```

### 配置 API Key

首次启动后，访问后台管理页面 http://127.0.0.1:5000/admin 配置：

| API | 用途 | 获取方式 |
|-----|------|----------|
| 即梦 4.5 | 2D 图像生成 | [火山引擎控制台](https://console.volcengine.com/) |
| Doubao-Seed3D | 3D 模型重建 | [火山引擎控制台](https://console.volcengine.com/) |
| Mimo V2.5 | AI 助手对话 | [火山引擎控制台](https://console.volcengine.com/) |

### 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `admin123` |

---

## 📖 功能详解

### 🎨 2D 图像生成

将灵感素材转化为精美的 2D 图像：

1. **选择灵感素材** — 从素材库上传或选择灵感图片
2. **选择风格模板** — Q版手办、写实、赛博朋克、水墨等
3. **AI 生成** — 调用即梦 4.5 API 生成图像
4. **抽卡机制** — 不满意可重新生成，满意可收入素材库

### 🧊 3D 模型重建

将 2D 图像转化为可交互的 3D 模型：

1. **选择 2D 图像** — 从素材库或生成结果中选择
2. **AI 重建** — 调用 Doubao-Seed3D-2.0 进行 3D 重建
3. **自动预处理** — 格式转换、尺寸缩放、压缩优化
4. **实时预览** — Three.js 渲染，支持 GLB/OBJ 格式

### 📁 素材库管理

- ✅ 收藏 / 删除 / 恢复
- ✅ 批量操作（批量删除、批量下载）
- ✅ 回收站机制
- ✅ 3D 模型实时预览

### ⚙️ 后台管理

- 🎨 风格模板管理（CRUD + 拖拽排序）
- 🖼️ 灵感素材管理
- 🔑 API 配置管理
- 📊 数据统计

---

## 🏗️ 技术架构

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端** | Flask + SQLite | RESTful API，轻量级数据库 |
| **前端** | HTML/CSS/JS + Three.js | 原生实现，3D 渲染引擎 |
| **AI 服务** | 火山引擎 Doubao 系列 | 2D 生成 + 3D 重建 + 对话 |

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                              │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │   index.html     │  │   admin.html     │                 │
│  │   (前端主页面)    │  │   (后台管理)      │                 │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask 后端服务                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  认证模块    │ │  生成模块    │ │  管理模块    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    外部 AI 服务                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  即梦 4.5   │ │  Seed3D     │ │  Mimo V2.5  │           │
│  │  (2D生成)   │ │  (3D重建)   │ │  (AI对话)   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 关键技术点

- **图片预处理流水线** — RGBA→RGB 转换、超大图片缩放、JPEG 压缩优化
- **任务队列管理** — 异步轮询、状态管理、失败重试机制
- **算力点系统** — 用户资源管理、失败自动退还
- **3D 渲染优化** — 磨砂材质、三层光效、ACES 色调映射

---

## 📡 API 设计

### 第三方 AI API

| API | 模型 | 用途 |
|-----|------|------|
| 火山引擎 Doubao-Seedream-4.5 | doubao-seedream-4-5-251128 | 2D 图像风格化生成 |
| 火山引擎 Doubao-Seed3D-2.0 | doubao-seed3d-2-0-260328 | 2D → 3D 模型重建 |
| 火山引擎 Mimo V2.5 | mimo-v2.5 | AI Agent 对话 |

### 项目 API 端点

项目提供了完整的 RESTful API，涵盖以下模块：

| 模块 | 端点数 | 说明 |
|------|--------|------|
| 认证 | 3 | 登录、注册、用户信息 |
| 灵感素材 | 3 | 增删查 |
| 风格模板 | 3 | 增删查 + 排序 |
| 素材库 | 6 | CRUD + 批量操作 |
| 回收站 | 3 | 查看、删除、清空 |
| 生成 | 2 | 2D 生成、3D 生成 |
| 任务 | 3 | 查询、删除 |
| 算力点 | 2 | 查询、扣除 |
| API Key | 3 | 管理 |
| 后台管理 | 12 | 完整管理功能 |

> 📚 完整 API 文档请访问 http://127.0.0.1:5000 查看

---

## 📋 项目结构

```
AI_3D_Platform_Demo/
├── app.py                      # Flask 后端主文件（1,800+ 行）
├── static/
│   ├── index.html              # 前端主页面（3,600+ 行）
│   ├── admin.html              # 后台管理页面（1,100+ 行）
│   ├── images/                 # 静态图片资源
│   └── uploads/                # 用户上传文件
│       ├── inspirations/       # 灵感素材
│       ├── library/            # 素材库图片
│       ├── models/             # 3D 模型文件
│       └── styles/             # 风格模板图片
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明
└── V1_RELEASE.md               # v1 结项文档
```

---

## 🔮 未来规划

### v1.1 — 无限画布

- 🖼️ 画布缩放 / 平移
- 🔗 节点连线
- 🎨 多素材组合编排
- 📐 自由布局设计

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目基于 MIT License 开源。

---

## 👤 作者

**Jasonlieee**

- GitHub: [@Jasonlieee](https://github.com/Jasonlieee)

---

> 🌟 如果这个项目对您有帮助，请给个 Star 支持一下！
