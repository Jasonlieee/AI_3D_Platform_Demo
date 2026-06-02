# AI 手办多模态设计平台

一个基于 AI 的 3D 手办设计平台，支持 2D 图像生成和 3D 模型重建。

## 功能特性

### 2D 图像生成
- 支持多种风格模板（Q版手办、写实、赛博朋克、水墨等）
- 调用即梦 4.5 (Doubao-Seedream-4.5) API
- 抽卡机制，可重新生成或收入素材库

### 3D 模型生成
- 调用 Doubao-Seed3D-2.0 API
- 支持 2D → 3D 模型重建
- 自动图片预处理（格式转换、尺寸缩放、压缩）
- 支持 GLB/OBJ 格式

### 素材库管理
- 收藏/删除/回收站
- 批量操作
- 3D 模型实时预览（Three.js）

### 后台管理系统
- 独立登录体系
- 风格模板管理
- 灵感素材管理
- API 配置管理

## 技术栈

- **后端**: Flask + SQLite
- **前端**: 原生 HTML/CSS/JS + Three.js r128
- **AI API**: 火山引擎 Doubao 系列

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

启动后访问后台管理页面 (http://127.0.0.1:5000/admin)，在 API 配置中填入：
- 即梦 4.5 API Key
- Doubao-Seed3D-2.0 API Key

### 3. 启动服务

```bash
python app.py
```

访问 http://127.0.0.1:5000

### 默认管理员账号

- 用户名: `admin`
- 密码: `admin123`

## 项目结构

```
AI_3D_Platform_Demo/
├── app.py                 # Flask 后端主文件
├── static/
│   ├── index.html         # 前端主页面
│   ├── admin.html         # 后台管理页面
│   └── uploads/           # 上传文件目录
├── requirements.txt       # Python 依赖
└── README.md             # 项目说明
```

## API 接口

### 认证类
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册

### 生成类
- `POST /api/generate/2d` - 2D 图像生成
- `POST /api/generate/3d` - 3D 模型生成

### 素材库类
- `GET /api/library` - 获取素材库
- `POST /api/library` - 收藏到素材库

### 后台管理类
- `POST /api/admin/login` - 管理员登录
- `GET /api/admin/styles` - 获取风格列表

## 许可证

MIT License
