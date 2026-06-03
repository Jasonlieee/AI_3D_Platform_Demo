# AI 手办多模态设计平台 - 项目自阅文档

> **本文档供 Trae IDE 快速了解项目全貌，包含技术架构、前后端构成、产品需求等关键信息。**

---

## 一、项目概述

**项目名称：** AI 手办多模态设计平台 (AI Figure Multimodal Design Platform)

**核心功能：** 将真人照片/2D图像通过 AI 转换为 3D 手办模型，支持多风格模板、实时预览、素材库管理。

**产品定位：** B端+C端混合模式的 AI 创意设计工具，面向手办设计师、潮玩商家、创意爱好者。

---

## 二、技术架构

### 2.1 技术栈总览

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端** | Python 3.8+ / Flask 3.0+ | RESTful API 服务 |
| **数据库** | SQLite | 轻量级本地数据库，支持 WAL 模式 |
| **前端** | HTML5 / CSS3 / JavaScript (原生) | 单页面应用，无框架依赖 |
| **3D 渲染** | Three.js r128 | 支持 GLB/OBJ 模型加载与预览 |
| **AI 服务** | 火山引擎 Doubao 系列 | 2D生成 + 3D重建 + AI对话 |

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户界面层 (Frontend)                      │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │   index.html     │  │   admin.html     │                 │
│  │   (主业务页面)    │  │   (后台管理)      │                 │
│  │   约 4000+ 行    │  │   约 1500+ 行    │                 │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Flask 后端服务 (app.py)                     │
│                  约 2000+ 行，单文件架构                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  认证模块    │ │  生成模块    │ │  管理模块    │           │
│  │   Auth      │ │  Generate   │ │   Admin     │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   数据存储层                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  SQLite DB  │ │  静态文件    │ │  上传文件    │           │
│  │  app.db     │ │  static/    │ │  uploads/   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               外部 AI 服务 (火山引擎)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  即梦 4.5   │ │  Seed3D     │ │  Mimo V2.5  │           │
│  │  (2D生成)   │ │  (3D重建)   │ │  (AI对话)   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、后端架构详解 (app.py)

### 3.1 文件结构

```
app.py (单文件，约 2000 行)
├── 配置区 (第1-25行)
│   ├── SECRET_KEY
│   ├── CORS 配置
│   └── 上传限制 (10MB)
│
├── 数据库初始化 (第54-324行)
│   ├── init_db() - 建表与迁移
│   ├── 8 张数据表
│   └── 默认数据初始化
│
├── 认证系统 (第373-428行)
│   ├── generate_token() - JWT 风格 Token
│   ├── verify_token() - Token 验证
│   ├── require_auth() - 登录装饰器
│   └── require_admin() - 管理员装饰器
│
├── 核心 API 路由 (第498-1234行)
│   ├── 认证 API (/api/auth/*)
│   ├── 灵感素材 API (/api/inspirations/*)
│   ├── 风格模板 API (/api/styles/*)
│   ├── 素材库 API (/api/library/*)
│   ├── 回收站 API (/api/recycle/*)
│   ├── 生成 API (/api/generate/*)
│   ├── 任务 API (/api/tasks/*)
│   ├── 算力点 API (/api/points/*)
│   ├── API密钥 API (/api/apikeys/*)
│   └── 后台管理 API (/api/admin/*)
│
├── AI 服务调用 (第1238-1761行)
│   ├── get_api_config() - 从数据库读取 API 配置
│   ├── call_jimo_api() - 调用即梦 4.5 (2D生成)
│   ├── call_seed3d_api() - 调用 Seed3D (3D重建)
│   ├── call_mimo_api() - 调用 Mimo (AI对话)
│   ├── upload_to_imgbb() - 上传图床
│   └── download_image_to_local() - 下载远程图片
│
└── Agent 对话 API (第1764-1812行)
```

### 3.2 数据库表结构

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `users` | 用户表 | username, password_hash, role, compute_points |
| `admins` | 管理员表 | username, password_hash |
| `styles` | 风格模板 | id, name, prompt, img, sort_order |
| `inspirations` | 灵感素材 | title, content, img, user_id |
| `library` | 素材库 | id, user_id, img, model_url, asset_type, prompt, style_id |
| `api_keys` | API密钥 | user_id, key_hash, key_prefix, scopes |
| `tasks` | 任务队列 | user_id, task_type, status, input_data, result_data, points_cost |
| `api_calls` | API调用记录 | user_id, api_type, params, status |
| `api_config` | API配置 | id, api_key, base_url, model_name |

### 3.3 核心 API 端点

```
认证相关:
POST   /api/auth/login          # 用户登录
POST   /api/auth/register       # 用户注册
GET    /api/auth/me             # 获取当前用户信息

素材管理:
GET    /api/inspirations        # 获取灵感列表
POST   /api/inspirations        # 上传灵感素材
DELETE /api/inspirations/<id>   # 删除灵感

风格模板:
GET    /api/styles              # 获取风格列表
POST   /api/styles              # 更新风格模板
POST   /api/styles/reorder      # 风格排序

素材库:
GET    /api/library             # 获取素材列表
POST   /api/library             # 添加素材入库
DELETE /api/library/<id>        # 删除素材
DELETE /api/library/batch       # 批量删除

AI 生成:
POST   /api/generate/2d         # 2D图像生成 (消耗10点)
POST   /api/generate/3d         # 3D模型生成 (消耗50点)

任务管理:
GET    /api/tasks               # 获取任务列表
GET    /api/tasks/<id>          # 获取任务详情
DELETE /api/tasks/batch         # 批量删除任务

算力点:
GET    /api/points              # 查询算力点
POST   /api/points/deduct       # 扣除算力点

后台管理:
POST   /api/admin/login         # 管理员登录
GET    /api/admin/stats/daily   # 每日统计
GET    /api/admin/api-configs   # API配置列表
PUT    /api/admin/api-configs/<id> # 更新API配置
CRUD   /api/admin/styles/*      # 风格管理
CRUD   /api/admin/inspirations/* # 灵感管理
```

---

## 四、前端架构详解

### 4.1 主页面 (index.html)

**文件大小：** 约 4000+ 行（HTML + CSS + JS 混合）

**页面结构：**
```
index.html
├── <style> 全局样式 (约 300 行)
│   ├── CSS 变量 (暗夜/白昼模式)
│   ├── 布局样式
│   ├── 组件样式
│   └── 动画效果
│
├── <body> 页面结构
│   ├── .sidebar - 左侧导航栏
│   │   ├── 创作大厅
│   │   ├── 我的素材库
│   │   ├── 无限编辑画布 (Beta)
│   │   ├── 任务队列
│   │   ├── 算力点与额度管理
│   │   ├── 企业账单与套餐
│   │   └── 回收站
│   │
│   ├── .main-content - 主内容区
│   │   ├── .top-header - 顶部栏
│   │   │   ├── 主题切换
│   │   │   ├── 系统通知
│   │   │   ├── 算力点显示
│   │   │   └── 用户菜单
│   │   │
│   │   └── .container - 视图容器
│   │       ├── #view-home - 创作大厅
│   │       ├── #view-upload - 上传配置
│   │       ├── #view-loading - 加载中
│   │       ├── #view-2d-result - 2D结果
│   │       ├── #view-canvas - 无限画布
│   │       ├── #view-library - 素材库
│   │       ├── #view-tasks - 任务队列
│   │       ├── #view-3d-result - 3D预览
│   │       ├── #view-points-manage - 算力管理
│   │       ├── #view-billing - 账单
│   │       └── #view-recycle - 回收站
│   │
│   └── .modal-overlay - 模态框
│
└── <script> JavaScript 逻辑 (约 2000+ 行)
    ├── 全局状态变量
    ├── API 调用函数
    ├── 页面渲染函数
    ├── 事件处理函数
    ├── Three.js 3D渲染
    └── 工具函数
```

### 4.2 后台管理页面 (admin.html)

**文件大小：** 约 1500+ 行

**访问地址：** http://127.0.0.1:5000/admin

**功能模块：**

| 标签页 | 功能 | 说明 |
|--------|------|------|
| **风格模版管理** | CRUD + 拖拽排序 | 管理所有 2D 风格模板（Q版/写实/机甲/国风） |
| **灵感素材管理** | CRUD | 管理灵感瀑布流素材，支持上传图片、编辑标题和描述 |
| **素材库管理** | 查看所有素材 | 包括用户上传的、AI生成的所有图片和3D模型记录 |
| **任务队列** | 查看所有任务 | 包括2D生成、3D重建的任务状态、消耗点数、完成时间 |
| **API调用统计** | 调用次数统计 | 总调用次数、图像模型调用、3D模型调用、最近14天趋势图表 |
| **API配置管理** | 修改API密钥 | 即梦、Seed3D、Mimo 的 API Key、Base URL、Model Name |

**数据管理详情：**
- **素材库数据**：可查看所有用户的素材，包括 ID、用户ID、类型（2D/3D）、预览图、创建时间
- **任务数据**：可查看所有任务，包括任务ID、用户ID、类型、状态（pending/processing/completed/failed）、消耗点数、创建时间、完成时间
- **API统计**：可查看总调用次数、图像模型调用次数、3D模型调用次数，以及最近14天的调用趋势图表

### 4.3 前端技术特点

1. **原生 JavaScript** - 无框架依赖，直接操作 DOM
2. **CSS 变量** - 支持暗夜/白昼主题切换
3. **Three.js** - 3D 模型渲染，支持 GLB/OBJ 格式
4. **响应式布局** - Flexbox + Grid 布局
5. **本地状态管理** - 全局变量管理应用状态

---

## 五、产品需求与功能

### 5.1 核心业务流程

```
用户上传照片/图片
        ↓
选择风格模板 (Q版/写实/机甲/国风)
        ↓
AI 生成 2D 手办图 (即梦 4.5 API)
        ↓
用户确认/重抽 (抽卡机制)
        ↓
AI 生成 3D 模型 (Seed3D API)
        ↓
Three.js 实时预览
        ↓
保存到素材库
```

### 5.2 功能模块清单

| 模块 | 功能 | 状态 |
|------|------|------|
| **创作大厅** | 模式选择、灵感瀑布流 | ✅ 已完成 |
| **2D 生成** | 上传图片、选择风格、AI生成 | ✅ 已完成 |
| **3D 重建** | 2D转3D、GLB/OBJ支持 | ✅ 已完成 |
| **素材库** | 收藏、删除、恢复、批量操作 | ✅ 已完成 |
| **无限画布** | 拖拽编辑、节点连线 | 🚧 Beta |
| **任务队列** | 异步任务、状态管理 | ✅ 已完成 |
| **算力系统** | 点数管理、自动退还 | ✅ 已完成 |
| **后台管理** | 风格/灵感/API配置管理 | ✅ 已完成 |
| **AI Agent** | 智能对话助手 | 🚧 开发中 |

### 5.3 用户角色

| 角色 | 权限 | 默认账号 |
|------|------|----------|
| **普通用户** | 使用生成、管理素材 | 注册创建 |
| **管理员** | 后台管理、查看所有数据 | admin / admin123 |

---

## 六、AI 服务配置

### 6.1 支持的 AI 服务

| 服务 | 用途 | 默认模型 |
|------|------|----------|
| **即梦 4.5** | 2D图像生成 | doubao-seedream-4-5-251128 |
| **Seed3D** | 3D模型重建 | doubao-seed3d-2-0-260328 |
| **Mimo V2.5** | AI对话 | mimo-v2.5 |

### 6.2 API 配置管理

API 配置存储在 `api_config` 表中，可通过后台管理页面动态修改：
- 访问 `/admin` 进入后台
- 在「API配置管理」中修改密钥和参数
- 修改后需重启后端生效

---

## 七、项目文件结构

```
AI_3D_Platform_Demo/
├── app.py                      # Flask 后端主文件 (核心)
├── static/
│   ├── index.html              # 前端主页面 (核心)
│   ├── admin.html              # 后台管理页面
│   ├── images/                 # 静态图片资源
│   │   ├── placeholder.svg     # 占位图
│   │   └── demo_*.jpg          # 演示截图
│   └── uploads/                # 用户上传文件 (运行时生成，不提交到Git)
│       ├── inspirations/       # 灵感素材图片
│       ├── library/            # 素材库图片（用户上传 + AI生成的2D图）
│       ├── models/             # 3D模型文件（GLB/OBJ格式）
│       ├── previews/           # 3D模型预览图
│       └── styles/             # 风格模板预览图
├── requirements.txt            # Python 依赖
├── .gitignore                  # Git 忽略配置
├── README.md                   # 项目说明文档
├── PROJECT_GUIDE.md            # 本文件 - 项目自阅文档
├── 启动AI手办平台.bat           # 启动 Flask 服务
├── 启动后台管理.bat             # 启动并打开后台
├── 启动Cloudflare隧道.bat      # 启动公网隧道
└── cloudflared.exe             # Cloudflare 隧道工具
```

---

## 八、启动与部署

### 8.1 环境要求

- Python 3.8+
- pip (Python 包管理)
- 火山引擎 API Key (用于 AI 服务)

### 8.2 安装依赖

```bash
pip install -r requirements.txt
```

**依赖列表：**
- flask >= 3.0.0
- flask-cors >= 4.0.0
- requests >= 2.31.0
- Pillow >= 10.0.0

### 8.3 启动服务

**方式一：使用启动脚本**
```bash
# 双击运行
启动AI手办平台.bat
```

**方式二：命令行启动**
```bash
python app.py
```

**启动后访问：**
- 主页面：http://127.0.0.1:5000
- 后台管理：http://127.0.0.1:5000/admin

### 8.4 公网部署

使用 Cloudflare Tunnel 实现公网访问：

```bash
# 启动隧道
.\cloudflared.exe tunnel --url http://localhost:5000
```

---

## 九、开发注意事项

### 9.1 代码特点

1. **单文件架构** - 后端所有逻辑在 `app.py` 中
2. **原生前端** - 无构建工具，直接编辑 HTML
3. **混合存储** - SQLite 数据库 + 文件系统
4. **同步调用** - AI API 调用为同步阻塞模式

### 9.2 常见修改场景

| 场景 | 修改文件 | 说明 |
|------|----------|------|
| 修改 API 逻辑 | app.py | 后端路由和业务逻辑 |
| 修改页面样式 | index.html | CSS 在 `<style>` 标签中 |
| 修改页面交互 | index.html | JS 在 `<script>` 标签中 |
| 修改后台功能 | admin.html | 后台管理页面 |
| 添加新风格 | app.py 或后台 | 在 init_db() 或后台添加 |

### 9.3 数据库操作

```python
# 获取数据库连接
db = get_db()

# 查询示例
user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

# 插入示例
db.execute("INSERT INTO table (col1, col2) VALUES (?, ?)", (val1, val2))
db.commit()
```

### 9.4 调试建议

1. 查看终端输出 - Flask 会打印请求日志和错误信息
2. 检查数据库 - 使用 SQLite 工具查看 `app.db`
3. 浏览器控制台 - 查看前端 JavaScript 错误
4. API 测试 - 使用 Postman 或 curl 测试接口

---

## 十、待优化项

1. **性能优化** - AI API 调用可改为异步模式
2. **前端重构** - 考虑使用 Vue/React 框架
3. **代码拆分** - app.py 拆分为多个模块
4. **安全加固** - 加强输入验证和 SQL 注入防护
5. **无限画布** - 完善画布功能和节点连线
6. **AI Agent** - 完善智能对话助手功能

---

## 十一、快速上手指南

### 新设备迁移步骤

1. **复制项目文件夹** 到新设备
2. **安装 Python 3.8+** 和 pip
3. **安装依赖：** `pip install -r requirements.txt`
4. **启动服务：** `python app.py`
5. **访问页面：** http://127.0.0.1:5000
6. **配置 API：** 访问 /admin 配置 AI 服务密钥

### 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |

---

**文档版本：** v1.0  
**最后更新：** 2026-06-03  
**维护者：** Jasonlieee
