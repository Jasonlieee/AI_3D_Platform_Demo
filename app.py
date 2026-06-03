import os
import base64
import uuid
import time
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
UPLOAD_FOLDER = os.path.join(STATIC_DIR, 'uploads')
DB_FILE = os.path.join(BASE_DIR, 'app.db')

app = Flask(__name__, static_folder=STATIC_DIR)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ai_3d_platform_fixed_secret_key_2024_v1')
CORS(app, resources={r"/api/*": {"origins": "*"}})

MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def is_local_request():
    """判断请求是否来自本地"""
    remote_ip = request.remote_addr
    # 支持反向代理时的 X-Forwarded-For 头
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        remote_ip = forwarded_for.split(',')[0].strip()
    return remote_ip in ('127.0.0.1', '::1', 'localhost')


@app.before_request
def restrict_admin_access():
    # 限制后台管理相关路由（API + 页面）
    # /admin 和 /admin.html 是后台页面
    # /api/admin/* 是后台API
    # /static/admin.html 是后台页面文件
    # 注意：通过Cloudflare Tunnel访问时，请求IP不是本地IP
    # 为了允许公网访问后台管理，已移除本地访问限制
    pass


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def migrate_from_data_json(db):
    """从旧的 data.json 文件迁移数据到 SQLite"""
    data_json_path = os.path.join(BASE_DIR, 'data.json')
    if not os.path.exists(data_json_path):
        return
    
    try:
        with open(data_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否已经迁移过
        check_styles = db.execute("SELECT id FROM styles WHERE id = 'chibi' AND img != ''").fetchone()
        check_inspirations = db.execute("SELECT COUNT(*) FROM inspirations").fetchone()[0]
        
        if check_styles and check_inspirations > 0:
            print("[OK] data.json 已迁移过，跳过")
            return
        
        print("[INFO] 开始从 data.json 迁移旧数据...")
        
        # 迁移 styles
        if 'styles_db' in data:
            for style in data['styles_db']:
                db.execute("INSERT OR REPLACE INTO styles (id, name, prompt, img) VALUES (?, ?, ?, ?)",
                          (style['id'], style['name'], style.get('prompt', ''), style.get('img', '')))
            print(f"  [OK] 迁移了 {len(data['styles_db'])} 个风格模板")
        
        # 迁移 inspirations
        if 'inspirations_db' in data:
            for insp in data['inspirations_db']:
                db.execute("INSERT OR REPLACE INTO inspirations (id, title, content, img) VALUES (?, ?, ?, ?)",
                          (insp['id'], insp['title'], insp.get('content', ''), insp.get('img', '')))
            print(f"  [OK] 迁移了 {len(data['inspirations_db'])} 个灵感素材")
        
        # 迁移 library
        if 'library_db' in data:
            for item in data['library_db']:
                asset_type = '2d' if item['id'].startswith('IMG-') else '3d'
                db.execute("INSERT OR REPLACE INTO library (id, user_id, img, asset_type) VALUES (?, ?, ?, ?)",
                          (item['id'], 1, item.get('img', ''), asset_type))
            print(f"  [OK] 迁移了 {len(data['library_db'])} 个个人素材")
        
        db.commit()
        print("[OK] data.json 旧数据迁移完成！")
    except Exception as e:
        print(f"[ERROR] 数据迁移失败: {e}")


def init_db():
    db = sqlite3.connect(DB_FILE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            compute_points INTEGER DEFAULT 10000,
            created_at TIMESTAMP DEFAULT (datetime('now', '+8 hours'))
        );

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT (datetime('now', '+8 hours'))
        );

        CREATE TABLE IF NOT EXISTS styles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            prompt TEXT NOT NULL,
            img TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS inspirations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 0,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            img TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT (datetime('now', '+8 hours'))
        );

        CREATE TABLE IF NOT EXISTS library (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            img TEXT DEFAULT '',
            model_url TEXT DEFAULT '',
            preview_url TEXT DEFAULT '',
            asset_type TEXT DEFAULT '2d',
            original_img TEXT DEFAULT '',
            prompt TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            name TEXT DEFAULT '',
            scopes TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            last_used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            input_data TEXT DEFAULT '{}',
            result_data TEXT DEFAULT '{}',
            points_cost INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT (datetime('now', '+8 hours')),
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            api_type TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            status TEXT DEFAULT 'success',
            created_at TIMESTAMP DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS api_config (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            api_key TEXT DEFAULT '',
            base_url TEXT DEFAULT '',
            model_name TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT (datetime('now', '+8 hours'))
        );
    """)
    
    # 数据库迁移：检查并添加缺失的列
    cursor = db.cursor()
    
    # 检查 library 表是否有 original_img 列
    cursor.execute("PRAGMA table_info(library)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'original_img' not in columns:
        print("[INFO] 正在添加 original_img 列到 library 表...")
        cursor.execute("ALTER TABLE library ADD COLUMN original_img TEXT DEFAULT ''")
        print("[OK] original_img 列添加成功")
    
    if 'prompt' not in columns:
        print("[INFO] 正在添加 prompt 列到 library 表...")
        cursor.execute("ALTER TABLE library ADD COLUMN prompt TEXT DEFAULT ''")
        print("[OK] prompt 列添加成功")
    
    if 'is_deleted' not in columns:
        print("[INFO] 正在添加 is_deleted 列到 library 表...")
        cursor.execute("ALTER TABLE library ADD COLUMN is_deleted INTEGER DEFAULT 0")
        print("[OK] is_deleted 列添加成功")
    
    if 'task_id' not in columns:
        print("[INFO] 正在添加 task_id 列到 library 表...")
        cursor.execute("ALTER TABLE library ADD COLUMN task_id TEXT DEFAULT ''")
        print("[OK] task_id 列添加成功")
    
    if 'style_id' not in columns:
        print("[INFO] 正在添加 style_id 列到 library 表...")
        cursor.execute("ALTER TABLE library ADD COLUMN style_id TEXT DEFAULT ''")
        print("[OK] style_id 列添加成功")
    
    # 检查 tasks 表是否有 error_message 列
    cursor.execute("PRAGMA table_info(tasks)")
    task_columns = [col[1] for col in cursor.fetchall()]
    
    if 'error_message' not in task_columns:
        print("[INFO] 正在添加 error_message 列到 tasks 表...")
        cursor.execute("ALTER TABLE tasks ADD COLUMN error_message TEXT DEFAULT ''")
        print("[OK] error_message 列添加成功")

    # 检查 inspirations 表是否有 user_id 列
    cursor.execute("PRAGMA table_info(inspirations)")
    insp_columns = [col[1] for col in cursor.fetchall()]

    if 'user_id' not in insp_columns:
        print("[INFO] 正在添加 user_id 列到 inspirations 表...")
        cursor.execute("ALTER TABLE inspirations ADD COLUMN user_id INTEGER DEFAULT 0")
        print("[OK] user_id 列添加成功")

    # 检查 styles 表是否有 sort_order 列
    cursor.execute("PRAGMA table_info(styles)")
    style_columns = [col[1] for col in cursor.fetchall()]

    if 'sort_order' not in style_columns:
        print("[INFO] 正在添加 sort_order 列到 styles 表...")
        cursor.execute("ALTER TABLE styles ADD COLUMN sort_order INTEGER DEFAULT 0")
        print("[OK] sort_order 列添加成功")

    default_styles = [
        ('chibi', '萌系 Q 版', '提取参考图片中人物的发型和服装特征，将其迁移至2D手办风格的泡泡玛特潮玩IP形象，从头到脚完整全身立绘，无任何裁切，严格遵循泡泡玛特标准2头身Q版比例（头部占整体高度1/2，头大身小），躯干短而紧凑，无拉长的上半身，圆润小短手，长度仅到腰际/胯部，不超过大腿上部，无过长手指，简化为肉乎乎的小手掌，与整体比例协调，腿部长度与躯干长度相当，比例协调无过短问题，泡泡玛特手办质感，黏土软胶肌理，平涂细腻上色，柔和均匀光影，哑光细腻质感，全身正视图，构图端正，纯白色极简背景，干净高级，超高清8K，细节丰富，真人特征柔和卡通化处理，整体比例协调统一', ''),
        ('realistic', '写实潮玩风', '提取参考图片中人物的发型和服装特征，将其迁移至写实日系PVC实体手办模型风格，基于参考形象提取发型与服装特征进行迁移还原，从头到脚完整全身立绘，画面必须包含完整头部、躯干、四肢与脚部，无任何裁切，还原真实人类身材比例，真实布料肌理质感，细腻哑光皮肤纹理，柔和高级商业影调，全身正视图，构图端正，纯白色极简背景，精致模型细节，高清渲染，8K画质，整体协调统一', ''),
        ('mecha', '赛博机甲风', '提取参考图片中人物的发型和服装特征，将其迁移至潮玩机甲手办风格，从头到脚完整全身立绘，画面必须包含完整头部、躯干、四肢与脚部，无任何裁切，严格遵循2:1标准潮玩Q版比例（头部占整体高度1/2，头大身小，躯干短而紧凑，四肢短小圆润，手部长度不超过腰际，与整体比例协调，无过长/畸形肢体，腿部与躯干长度匹配，无过短问题），提取原人物服装的轮廓与核心特征，将服装转化为机甲造型，保留原服装元素并融合精密机甲设计，光滑亮面机甲外壳，细腻金属光泽，精密机械关节与细节，机甲细节带有柔和发光效果，未来科技感，潮玩手办质感，类似泡泡玛特机甲IP风格，柔和均匀光影，全身正视图，构图端正，纯白色极简背景，干净高级，超高清8K，细节丰富，整体比例协调统一', ''),
        ('guofeng', '国风手办', '基于真人照片转化为国风潮玩手办 IP 形象，从头到脚完整全身立绘，画面完整包含头部、躯干、四肢、双脚，无画面裁切，严格遵循标准 2:3Q 版头身比例，头大身小，躯干短而紧凑，手掌短小圆润，手部长度不超过胯部，杜绝过长、畸形手部，四肢与腿部比例均衡协调；完整提取原图人物发型、五官轮廓、国风传统服饰核心特征并保留，古风新中式汉服，精致传统刺绣纹样，真实古风布料哑光肌理；泡泡玛特黏土软胶手办质感，细腻哑光黏土肌理，柔和暖调商业柔光，人物带有自然腮红，皮克斯风格的美式3d动漫五官；全身正视图，构图端正，白色纯色极简背景，画面干净高级，超高清 8K，细节丰富细腻，真人五官柔和卡通化处理，全身上下比例统一协调', '')
    ]
    for s in default_styles:
        db.execute("INSERT OR IGNORE INTO styles (id, name, prompt, img) VALUES (?, ?, ?, ?)", s)
    
    # 初始化API配置 (请在后台管理页面填入您的API密钥)
    default_apis = [
        ('jimo', '即梦4.5', 'YOUR_JIMO_API_KEY', 'https://ark.cn-beijing.volces.com/api/v3', 'doubao-seedream-4-5-251128'),
        ('mimo', 'Mimo V2.5', 'YOUR_MIMO_API_KEY', 'https://token-plan-cn.xiaomimimo.com/v1', 'mimo-v2.5'),
        ('seed3d', 'Doubao-Seed3D-2.0', 'YOUR_SEED3D_API_KEY', 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks', 'doubao-seed3d-2-0-260328')
    ]
    for api in default_apis:
        db.execute("INSERT OR IGNORE INTO api_config (id, name, api_key, base_url, model_name) VALUES (?, ?, ?, ?, ?)", api)
    
    existing_user = db.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not existing_user:
        pw_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        db.execute("INSERT INTO users (username, password_hash, role, compute_points) VALUES (?, ?, ?, ?)",
                   ('admin', pw_hash, 'admin', 10000))
    
    existing_admin = db.execute("SELECT id FROM admins WHERE username = 'admin'").fetchone()
    if not existing_admin:
        pw_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        db.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                   ('admin', pw_hash))
        print("[OK] 默认管理员创建成功！账号: admin 密码: admin123")
    
    # 从 data.json 迁移旧数据
    migrate_from_data_json(db)
    
    # 清理卡住的任务：将超过30分钟仍为processing的任务标记为failed并退还算力点
    try:
        stuck_tasks = db.execute("""
            SELECT id, user_id, points_cost FROM tasks 
            WHERE status = 'processing' 
            AND datetime(created_at, '+30 minutes') < datetime('now', '+8 hours')
        """).fetchall()
        for task in stuck_tasks:
            db.execute("UPDATE tasks SET status = 'failed', error_message = '任务因超时被自动清理', completed_at = datetime('now', '+8 hours') WHERE id = ?", (task[0],))
            if task[2] > 0:
                db.execute("UPDATE users SET compute_points = compute_points + ? WHERE id = ?", (task[2], task[1]))
            print(f"[INFO] 已清理超时任务 ID: {task[0]}，退还 {task[2]} 算力点")
        if stuck_tasks:
            db.commit()
    except Exception as e:
        print(f"[WARN] 清理超时任务失败: {e}")

    db.commit()
    db.close()
    print("[OK] 数据库初始化完成")


def generate_model_preview(model_url, model_id):
    """生成3D模型预览图（带3D图标的静态图片）"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 创建预览图目录
        preview_dir = os.path.join(UPLOAD_FOLDER, 'previews')
        os.makedirs(preview_dir, exist_ok=True)
        
        # 生成预览图文件名
        preview_name = f"preview_{model_id}.png"
        preview_path = os.path.join(preview_dir, preview_name)
        
        # 创建预览图 (400x400)
        img = Image.new('RGB', (400, 400), color=(26, 27, 35))
        draw = ImageDraw.Draw(img)
        
        # 绘制3D立方体图标
        # 立方体正面
        draw.rectangle([120, 120, 240, 240], outline=(100, 200, 255), width=3)
        # 立方体顶面
        draw.polygon([(120, 120), (160, 80), (280, 80), (240, 120)], outline=(100, 200, 255))
        # 立方体右面
        draw.polygon([(240, 120), (280, 80), (280, 200), (240, 240)], outline=(100, 200, 255))
        
        # 绘制文字
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((160, 280), "3D Model", fill=(150, 150, 150), font=font)
        draw.text((140, 320), "Click to view", fill=(100, 100, 100), font=font)
        
        # 保存预览图
        img.save(preview_path, 'PNG')
        print(f"[OK] 预览图已生成: {preview_path}")
        
        # 返回相对URL
        return f"/static/uploads/previews/{preview_name}"
        
    except Exception as e:
        print(f"[ERROR] 生成预览图失败: {e}")
        return None


def generate_token(user_id, username, role):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': (datetime.utcnow() + timedelta(days=7)).isoformat()
    }
    token_data = json.dumps(payload)
    token = base64.urlsafe_b64encode(token_data.encode()).decode()
    signature = hashlib.sha256(f"{token}{app.config['SECRET_KEY']}".encode()).hexdigest()[:32]
    return f"{token}.{signature}"


def verify_token(token):
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        token_data, signature = parts
        expected_sig = hashlib.sha256(f"{token_data}{app.config['SECRET_KEY']}".encode()).hexdigest()[:32]
        if signature != expected_sig:
            return None
        payload = json.loads(base64.urlsafe_b64decode(token_data))
        if datetime.fromisoformat(payload['exp']) < datetime.utcnow():
            return None
        return payload
    except Exception:
        return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'code': 401, 'message': '请先登录'}), 401
        payload = verify_token(token)
        if not payload:
            return jsonify({'code': 401, 'message': 'Token无效或已过期'}), 401
        request.user = payload
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'code': 401, 'message': '请先登录'}), 401
        payload = verify_token(token)
        if not payload or payload.get('role') != 'admin':
            return jsonify({'code': 403, 'message': '需要管理员权限'}), 403
        request.user = payload
        return f(*args, **kwargs)
    return decorated


def save_base64_image(base64_str, subfolder=""):
    if not base64_str:
        return ""
    if base64_str.startswith('/static/'):
        return base64_str
    if ',' not in base64_str:
        return ""
    try:
        header, encoded = base64_str.split(',', 1)
        file_ext = header.split(';')[0].split('/')[1]
        if file_ext == 'jpeg':
            file_ext = 'jpg'
        if file_ext == 'svg+xml':
            file_ext = 'svg'
        filename = f"{uuid.uuid4().hex}.{file_ext}"
        target_folder = os.path.join(UPLOAD_FOLDER, subfolder) if subfolder else UPLOAD_FOLDER
        os.makedirs(target_folder, exist_ok=True)
        filepath = os.path.join(target_folder, filename)
        encoded += "=" * ((4 - len(encoded) % 4) % 4)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(encoded))
        return f"/static/uploads/{subfolder}/{filename}" if subfolder else f"/static/uploads/{filename}"
    except Exception as e:
        print(f"图片保存失败: {e}")
        return ""

import urllib.request
import urllib.error
def download_external_image(url, subfolder="library"):
    """下载外部URL图片并保存到本地"""
    if not url or url.startswith('/static/'):
        return url  # 已经是本地URL
    try:
        print(f"[INFO] 正在下载外部图片: {url[:80]}...")
        # 使用 urllib 下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        
        # 尝试打开URL
        with urllib.request.urlopen(req, timeout=10) as response:
            # 确定文件扩展名
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            if 'png' in content_type:
                ext = 'png'
            elif 'gif' in content_type:
                ext = 'gif'
            else:
                ext = 'jpg'
            
            filename = f"{uuid.uuid4().hex}.{ext}"
            target_folder = os.path.join(UPLOAD_FOLDER, subfolder)
            os.makedirs(target_folder, exist_ok=True)
            filepath = os.path.join(target_folder, filename)
            
            # 保存文件
            with open(filepath, 'wb') as f:
                f.write(response.read())
            
            print(f"[INFO] 外部图片已保存: {filepath}")
            return f"/static/uploads/{subfolder}/{filename}"
    except Exception as e:
        print(f"[ERROR] 下载外部图片失败: {e}")
        return url  # 下载失败时返回原URL


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/admin')
@app.route('/admin.html')
def admin_page():
    return app.send_static_file('admin.html')


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, pw_hash)).fetchone()
    if not user:
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
    token = generate_token(user['id'], user['username'], user['role'])
    return jsonify({
        'code': 200,
        'data': {
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'compute_points': user['compute_points']
            }
        }
    })


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
        db.commit()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        token = generate_token(user['id'], user['username'], user['role'])
        return jsonify({'code': 200, 'data': {'token': token, 'user': {'id': user['id'], 'username': user['username'], 'compute_points': user['compute_points']}}})
    except sqlite3.IntegrityError:
        return jsonify({'code': 409, 'message': '用户名已存在'}), 409


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_me():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    return jsonify({
        'code': 200,
        'data': {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'compute_points': user['compute_points']
        }
    })


@app.route('/api/inspirations', methods=['GET', 'POST'])
def handle_inspirations():
    db = get_db()
    if request.method == 'GET':
        rows = db.execute("SELECT * FROM inspirations ORDER BY created_at DESC").fetchall()
        data = [{'id': r['id'], 'title': r['title'], 'content': r['content'], 'img': r['img']} for r in rows]
        return jsonify({'code': 200, 'data': data})
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        payload = verify_token(token) if token else None
        user_id = payload.get('user_id', 0) if payload else 0

        body = request.json
        img_url = save_base64_image(body.get('img', ''), subfolder="inspirations")
        db.execute("INSERT INTO inspirations (user_id, title, content, img) VALUES (?, ?, ?, ?)",
                   (user_id, body.get('title', '无标题灵感'), body.get('content', ''), img_url))
        db.commit()
        return jsonify({'code': 200, 'message': '上传成功'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/inspirations/<int:insp_id>', methods=['DELETE'])
def delete_inspiration(insp_id):
    db = get_db()
    db.execute("DELETE FROM inspirations WHERE id = ?", (insp_id,))
    db.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


@app.route('/api/styles', methods=['GET', 'POST'])
def handle_styles():
    db = get_db()
    if request.method == 'GET':
        rows = db.execute("SELECT * FROM styles ORDER BY sort_order ASC, id ASC").fetchall()
        data = [{'id': r['id'], 'name': r['name'], 'prompt': r['prompt'], 'img': r['img'], 'sort_order': r['sort_order']} for r in rows]
        return jsonify({'code': 200, 'data': data})
    body = request.json
    style_id = body.get('id')
    img_url = save_base64_image(body.get('img', ''), subfolder="styles")
    cursor = db.execute("UPDATE styles SET img = ? WHERE id = ?", (img_url, style_id))
    db.commit()
    if cursor.rowcount > 0:
        return jsonify({'code': 200, 'message': '模板更新成功'})
    return jsonify({'code': 404, 'message': '未找到对应风格ID'}), 404


@app.route('/api/styles/reorder', methods=['POST'])
@require_admin
def reorder_styles():
    db = get_db()
    body = request.json
    style_ids = body.get('style_ids', [])
    
    for i, style_id in enumerate(style_ids):
        db.execute("UPDATE styles SET sort_order = ? WHERE id = ?", (i, style_id))
    
    db.commit()
    return jsonify({'code': 200, 'message': '排序更新成功'})


def log_api_call(user_id, api_type, params=None, status='success'):
    try:
        db = get_db()
        db.execute("""
            INSERT INTO api_calls (user_id, api_type, params, status)
            VALUES (?, ?, ?, ?)
        """, (user_id, api_type, json.dumps(params or {}), status));
        db.commit()
    except Exception as e:
        print(f"[ERROR] 记录API调用失败: {e}")


@app.route('/api/admin/stats/daily', methods=['GET'])
@require_admin
def get_daily_stats():
    db = get_db()
    days = request.args.get('days', 14, type=int)
    
    rows = db.execute("""
        SELECT 
            DATE(created_at) as date,
            api_type,
            COUNT(*) as call_count
        FROM api_calls
        WHERE created_at >= date('now', ?)
        GROUP BY DATE(created_at), api_type
        ORDER BY date ASC
    """, (f'-{days} days',)).fetchall()
    
    date_map = {}
    for r in rows:
        date = r['date']
        if date not in date_map:
            date_map[date] = {'date': date, 'image_calls': 0, 'model3d_calls': 0, 'call_count': 0}
        if r['api_type'] == '3d_generation':
            date_map[date]['model3d_calls'] = r['call_count']
        else:
            date_map[date]['image_calls'] = r['call_count']
        date_map[date]['call_count'] += r['call_count']
    
    stats = list(date_map.values())
    
    total = db.execute("SELECT COUNT(*) as total_calls FROM api_calls").fetchone()
    total_2d = db.execute("SELECT COUNT(*) as c FROM api_calls WHERE api_type != '3d_generation'").fetchone()
    total_3d = db.execute("SELECT COUNT(*) as c FROM api_calls WHERE api_type = '3d_generation'").fetchone()
    
    return jsonify({
        'code': 200,
        'data': {
            'daily': stats,
            'summary': {
                'total_calls': total['total_calls'] if total['total_calls'] else 0,
                'image_calls': total_2d['c'] if total_2d['c'] else 0,
                'model3d_calls': total_3d['c'] if total_3d['c'] else 0
            }
        }
    })


@app.route('/api/admin/api-configs', methods=['GET'])
@require_admin
def get_api_configs():
    db = get_db()
    rows = db.execute("SELECT * FROM api_config ORDER BY id").fetchall()
    configs = []
    for r in rows:
        configs.append({
            'id': r['id'],
            'name': r['name'],
            'api_key': r['api_key'],
            'base_url': r['base_url'],
            'model_name': r['model_name'],
            'updated_at': r['updated_at']
        })
    return jsonify({'code': 200, 'data': configs})


@app.route('/api/admin/api-configs/<api_id>', methods=['PUT'])
@require_admin
def update_api_config(api_id):
    db = get_db()
    data = request.get_json()
    
    # 更新数据库
    db.execute("""
        UPDATE api_config 
        SET api_key = ?, base_url = ?, model_name = ?, updated_at = datetime('now', '+8 hours') 
        WHERE id = ?
    """, (data['api_key'], data['base_url'], data['model_name'], api_id))
    db.commit()
    
    return jsonify({'code': 200, 'message': 'API配置更新成功！请重启后端生效'})


@app.route('/api/library', methods=['GET', 'POST'])
@require_auth
def handle_library():
    db = get_db()
    if request.method == 'GET':
        is_admin = request.user.get('role') == 'admin'
        if is_admin:
            rows = db.execute("SELECT * FROM library WHERE is_deleted = 0 ORDER BY created_at DESC").fetchall()
        else:
            rows = db.execute("SELECT * FROM library WHERE is_deleted = 0 AND user_id = ? ORDER BY created_at DESC",
                              (request.user['user_id'],)).fetchall()
        data = []
        for r in rows:
            img = r['img']
            # 检查图片是否是base64字符串，如果是，尝试保存为文件
            if img and img.startswith('data:') and ',' in img:
                print(f"[INFO] 发现base64图片，正在保存: {r['id']}")
                img_url = save_base64_image(img, subfolder="library")
                if img_url:
                    # 更新数据库
                    db.execute("UPDATE library SET img = ? WHERE id = ?", (img_url, r['id']))
                    db.commit()
                    img = img_url
                    print(f"[INFO] base64图片已保存: {img_url}")
            # 检查是否是外部URL，如果是，尝试下载到本地
            elif img and (img.startswith('http://') or img.startswith('https://')):
                print(f"[INFO] 发现外部URL图片，正在下载: {r['id']}")
                img_url = download_external_image(img, subfolder="library")
                if img_url and img_url != img:  # 确认下载成功
                    # 更新数据库
                    db.execute("UPDATE library SET img = ? WHERE id = ?", (img_url, r['id']))
                    db.commit()
                    img = img_url
                    print(f"[INFO] 外部图片已下载并保存: {img_url}")
            # 修复MDL记录：如果img是placeholder或无效，尝试用original_img替换
            original_img = r['original_img'] if 'original_img' in r.keys() else ''
            if r['id'].startswith('MDL-') and (not img or img == '/static/images/placeholder.svg' or 'tos-cn-beijing.volces.com' in (img or '')):
                if original_img and original_img.startswith('/static/'):
                    db.execute("UPDATE library SET img = ? WHERE id = ?", (original_img, r['id']))
                    db.commit()
                    img = original_img
                    print(f"[INFO] MDL记录 {r['id']} 的img已修复为original_img: {img}")
            model_url_val = r['model_url'] if 'model_url' in r.keys() else ''
            preview_url_val = r['preview_url'] if 'preview_url' in r.keys() else ''
            prompt_val = r['prompt'] if 'prompt' in r.keys() else ''
            style_id_val = r['style_id'] if 'style_id' in r.keys() else ''
            asset_type_val = r['asset_type'] if 'asset_type' in r.keys() else '2d'

            tags = []
            is_mdl = r['id'].startswith('MDL-')
            if is_mdl and model_url_val:
                tags.append({'label': '3D模型', 'type': 'model'})
                lower_url = model_url_val.lower()
                if lower_url.endswith('.glb') or lower_url.endswith('.gltf'):
                    tags.append({'label': 'GLB', 'type': 'format-glb'})
                elif lower_url.endswith('.obj'):
                    tags.append({'label': 'OBJ', 'type': 'format-obj'})
            elif asset_type_val == '3d':
                tags.append({'label': '3D模型', 'type': 'model'})
            else:
                tags.append({'label': '2D图片', 'type': '2d'})
            if prompt_val or style_id_val:
                tags.append({'label': 'AI生成', 'type': 'ai'})
            if preview_url_val:
                tags.append({'label': '有预览', 'type': 'preview'})

            data.append({'id': r['id'], 'user_id': r['user_id'],
                        'date': r['created_at'][:10] if r['created_at'] else '', 
                        'img': img, 'asset_type': asset_type_val,
                        'original_img': r['original_img'], 'prompt': prompt_val,
                        'task_id': r['task_id'] if 'task_id' in r.keys() else '',
                        'style_id': style_id_val,
                        'model_url': model_url_val,
                        'preview_url': preview_url_val,
                        'tags': tags})
        print(f"[INFO] 返回 {len(data)} 个素材库项目")
        for item in data[:2]:
            print(f"  - {item['id']}: {item['img']}")
        return jsonify({'code': 200, 'data': data})
    try:
        body = request.json
        img_input = body.get('img', '')
        original_img = body.get('original_img', '')
        prompt = body.get('prompt', '')
        task_id = body.get('task_id', '')
        style_id = body.get('style_id', '')
        model_url = body.get('model_url', '')
        preview_url = body.get('preview_url', '')
        
        print(f"[INFO] 素材入库: id={body.get('id')}, img_type={type(img_input)}, img_start={img_input[:80] if img_input else 'empty'}")
        print(f"[INFO] 原图: {original_img}, 提示词: {prompt[:50] if prompt else '无'}, 任务ID: {task_id}, 风格ID: {style_id}, 模型URL: {model_url}, 预览URL: {preview_url}")
        
        img_url = ""
        # 如果是本地URL，直接使用
        if img_input and img_input.startswith('/static/'):
            img_url = img_input
            print(f"[INFO] 使用原始URL: {img_url}")
        # 如果是外部http URL，下载到本地
        elif img_input and (img_input.startswith('http://') or img_input.startswith('https://')):
            img_url = download_external_image(img_input, subfolder="library")
            print(f"[INFO] 外部图片下载结果: {img_url}")
        else:
            # 否则尝试保存base64
            img_url = save_base64_image(img_input, subfolder="library")
            print(f"[INFO] 保存base64图片: {img_url}")
        
        if not img_url:
            print(f"[ERROR] 图片数据无效，img_input={repr(img_input)}")
            return jsonify({'code': 400, 'message': '图片数据无效'}), 400
        
        item_id = body.get('id', f"MDL-{int(time.time())}")
        asset_type = '2d' if item_id.startswith('IMG-') else '3d'
        
        # 如果是3D模型且没有预览图，生成一个
        if asset_type == '3d' and model_url and not preview_url:
            preview_url = generate_model_preview(model_url, item_id)
        
        # 保存所有字段，包括原图、提示词、任务ID、风格ID、模型URL和预览URL
        db.execute("INSERT OR REPLACE INTO library (id, user_id, img, asset_type, original_img, prompt, task_id, style_id, model_url, preview_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (item_id, request.user['user_id'], img_url, asset_type, original_img, prompt, task_id, style_id, model_url, preview_url))
        db.commit()
        print(f"[OK] 素材入库成功: {item_id} -> {img_url}")
        return jsonify({'code': 200, 'message': '素材入库成功', 'data': {'id': item_id}})
    except Exception as e:
        import traceback
        error_msg = f"素材入库失败: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/library/<item_id>', methods=['DELETE'])
def delete_library_item(item_id):
    db = get_db()
    cursor = db.execute("UPDATE library SET is_deleted = 1 WHERE id = ?", (item_id,))
    db.commit()
    if cursor.rowcount > 0:
        return jsonify({'code': 200, 'message': '删除成功'})
    return jsonify({'code': 404, 'message': '未找到该素材'}), 404


@app.route('/api/library/<item_id>/restore', methods=['POST'])
def restore_library_item(item_id):
    db = get_db()
    cursor = db.execute("UPDATE library SET is_deleted = 0 WHERE id = ?", (item_id,))
    db.commit()
    if cursor.rowcount > 0:
        return jsonify({'code': 200, 'message': '恢复成功'})
    return jsonify({'code': 404, 'message': '未找到该素材'}), 404


@app.route('/api/recycle', methods=['GET'])
def get_recycle_bin():
    db = get_db()
    rows = db.execute("SELECT * FROM library WHERE is_deleted = 1 ORDER BY created_at DESC").fetchall()
    data = [{'id': r['id'], 'date': r['created_at'][:10] if r['created_at'] else '', 
             'img': r['img'], 'asset_type': r['asset_type'],
             'original_img': r['original_img'], 'prompt': r['prompt']} 
            for r in rows]
    return jsonify({'code': 200, 'data': data})


@app.route('/api/recycle/<item_id>', methods=['DELETE'])
def permanently_delete_item(item_id):
    db = get_db()
    cursor = db.execute("DELETE FROM library WHERE id = ?", (item_id,))
    db.commit()
    if cursor.rowcount > 0:
        return jsonify({'code': 200, 'message': '永久删除成功'})
    return jsonify({'code': 404, 'message': '未找到该素材'}), 404


@app.route('/api/recycle/clear', methods=['POST'])
def clear_recycle_bin():
    db = get_db()
    cursor = db.execute("DELETE FROM library WHERE is_deleted = 1")
    db.commit()
    return jsonify({'code': 200, 'message': f'已永久删除 {cursor.rowcount} 个素材'})


@app.route('/api/points', methods=['GET'])
@require_auth
def get_points():
    db = get_db()
    user = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
    return jsonify({'code': 200, 'data': {'points': user['compute_points'] if user else 0}})


@app.route('/api/points/deduct', methods=['POST'])
@require_auth
def deduct_points():
    data = request.json
    amount = data.get('amount', 0)
    db = get_db()
    user = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
    if not user or user['compute_points'] < amount:
        return jsonify({'code': 400, 'message': '算力点不足'}), 400
    db.execute("UPDATE users SET compute_points = compute_points - ? WHERE id = ?", (amount, request.user['user_id']))
    db.commit()
    new_points = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
    return jsonify({'code': 200, 'data': {'points': new_points['compute_points']}})


@app.route('/api/apikeys', methods=['GET', 'POST'])
@require_auth
def handle_api_keys():
    db = get_db()
    if request.method == 'GET':
        rows = db.execute("SELECT id, key_prefix, name, scopes, is_active, last_used_at, created_at FROM api_keys WHERE user_id = ?",
                          (request.user['user_id'],)).fetchall()
        data = [{'id': r['id'], 'key_prefix': r['key_prefix'], 'name': r['name'],
                 'scopes': json.loads(r['scopes']), 'is_active': bool(r['is_active']),
                 'last_used_at': r['last_used_at'], 'created_at': r['created_at']} for r in rows]
        return jsonify({'code': 200, 'data': data})
    body = request.json
    raw_key = f"sk-ai-{secrets.token_hex(20)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:16] + "..."
    scopes = json.dumps(body.get('scopes', ['image_gen', '3d_mesh']))
    db.execute("INSERT INTO api_keys (user_id, key_hash, key_prefix, name, scopes) VALUES (?, ?, ?, ?, ?)",
               (request.user['user_id'], key_hash, key_prefix, body.get('name', ''), scopes))
    db.commit()
    return jsonify({'code': 200, 'data': {'key': raw_key, 'key_prefix': key_prefix}, 'message': '密钥创建成功，仅显示一次'})


@app.route('/api/apikeys/<int:key_id>', methods=['DELETE'])
@require_auth
def delete_api_key(key_id):
    db = get_db()
    cursor = db.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, request.user['user_id']))
    db.commit()
    if cursor.rowcount > 0:
        return jsonify({'code': 200, 'message': '密钥已删除'})
    return jsonify({'code': 404, 'message': '未找到该密钥'}), 404


@app.route('/api/tasks', methods=['GET'])
@require_auth
def get_tasks():
    db = get_db()
    is_admin = request.user.get('role') == 'admin'
    if is_admin:
        rows = db.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100").fetchall()
    else:
        rows = db.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
                          (request.user['user_id'],)).fetchall()
    data = []
    for r in rows:
        task_data = {
            'id': r['id'],
            'user_id': r['user_id'],
            'task_type': r['task_type'],
            'status': r['status'],
            'points_cost': r['points_cost'],
            'created_at': r['created_at'],
            'completed_at': r['completed_at'],
            'input_data': json.loads(r['input_data']) if r['input_data'] else {},
            'result': json.loads(r['result_data']) if r['result_data'] else {},
            'error': r['error_message'] if 'error_message' in r.keys() else ''
        }
        data.append(task_data)
    return jsonify({'code': 200, 'data': data})


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@require_auth
def get_task_detail(task_id):
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                      (task_id, request.user['user_id'])).fetchone()
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404
    return jsonify({
        'code': 200,
        'data': {
            'id': task['id'],
            'task_type': task['task_type'],
            'status': task['status'],
            'points_cost': task['points_cost'],
            'created_at': task['created_at'],
            'completed_at': task['completed_at'],
            'input_data': json.loads(task['input_data']) if task['input_data'] else {},
            'result': json.loads(task['result_data']) if task['result_data'] else {},
            'error': task['error_message'] if 'error_message' in task.keys() else ''
        }
    })


# ================= 批量操作API =================
@app.route('/api/library/batch', methods=['DELETE'])
@require_auth
def batch_delete_library():
    data = request.json
    item_ids = data.get('ids', [])
    if not item_ids:
        return jsonify({'code': 400, 'message': '请提供要删除的素材ID列表'}), 400
    db = get_db()
    placeholders = ','.join(['?'] * len(item_ids))
    cursor = db.execute(f"UPDATE library SET is_deleted = 1 WHERE id IN ({placeholders})", item_ids)
    db.commit()
    return jsonify({'code': 200, 'message': f'已将 {cursor.rowcount} 个素材移到回收站'})


@app.route('/api/tasks/batch', methods=['DELETE'])
@require_auth
def batch_delete_tasks():
    try:
        data = request.json
        task_ids = data.get('ids', [])
        print(f"[DEBUG] 批量删除任务: ids={task_ids}, user_id={request.user['user_id']}")
        if not task_ids:
            return jsonify({'code': 400, 'message': '请提供要删除的任务ID列表'}), 400
        db = get_db()
        int_ids = [int(tid) for tid in task_ids]
        placeholders = ','.join(['?'] * len(int_ids))
        cursor = db.execute(f"DELETE FROM tasks WHERE id IN ({placeholders}) AND user_id = ?", int_ids + [request.user['user_id']])
        db.commit()
        print(f"[OK] 批量删除完成: 删除了 {cursor.rowcount} 个任务")
        return jsonify({'code': 200, 'message': f'已删除 {cursor.rowcount} 个任务'})
    except Exception as e:
        print(f"[ERROR] 批量删除任务失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'删除失败: {str(e)}'}), 500


@app.route('/api/library/batch/download', methods=['POST'])
@require_auth
def batch_download_library():
    data = request.json
    item_ids = data.get('ids', [])
    if not item_ids:
        return jsonify({'code': 400, 'message': '请提供要下载的素材ID列表'}), 400
    db = get_db()
    placeholders = ','.join(['?'] * len(item_ids))
    rows = db.execute(f"SELECT id, img FROM library WHERE id IN ({placeholders}) AND is_deleted = 0", item_ids).fetchall()
    data = [{'id': r['id'], 'img': r['img']} for r in rows]
    return jsonify({'code': 200, 'data': data})


@app.route('/api/generate/2d', methods=['POST'])
@require_auth
def generate_2d():
    data = request.json
    image_data = data.get('image', '')
    style_id = data.get('style_id', 'chibi')
    
    if not image_data:
        return jsonify({'code': 400, 'message': '请上传图片'}), 400
    
    # 从数据库获取对应风格的提示词
    db = get_db()
    style = db.execute("SELECT prompt FROM styles WHERE id = ?", (style_id,)).fetchone()
    if style:
        chibi_prompt = style['prompt']
    else:
        # 如果找不到对应风格，使用默认提示词
        chibi_prompt = "将图中人物转换为可爱的Q版2D手办风格，chibi风格，可爱，精致，手办质感，高画质"
    
    user = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
    
    if not user or user['compute_points'] < 10:
        return jsonify({'code': 400, 'message': '算力点不足，需要10点'}), 400
    
    # 创建任务
    db.execute("INSERT INTO tasks (user_id, task_type, status, input_data, points_cost) VALUES (?, ?, ?, ?, ?)",
               (request.user['user_id'], '2d_generation', 'processing',
                json.dumps({'style_id': style_id, 'prompt': chibi_prompt}), 10))
    db.execute("UPDATE users SET compute_points = compute_points - 10 WHERE id = ?", (request.user['user_id'],))
    db.commit()
    
    task_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # 保存原图（如果有）
    original_img_url = None
    if image_data:
        original_img_url = save_base64_image(image_data, subfolder="library")
    
    print(f"[INFO] 开始调用即梦API生成手办，任务ID: {task_id}")
    print(f"[INFO] 模式: {'图生图' if image_data else '文生图'}")
    
    # 调用即梦API，使用3:4比例
    image_urls, error = call_jimo_api(chibi_prompt, image_data=image_data, size="1728x2304", n=1)
    
    # 记录API调用
    if error:
        log_api_call(request.user['user_id'], '2d_generation', params={'style_id': style_id}, status='failed')
        # 如果API调用失败，更新任务状态并返回错误
        result_data = {'original_img': original_img_url} if original_img_url else {}
        db.execute("UPDATE tasks SET status = 'failed', result_data = ?, error_message = ?, completed_at = datetime('now', '+8 hours') WHERE id = ?",
                   (json.dumps(result_data), error, task_id))
        db.commit()
        # 退还算力点
        db.execute("UPDATE users SET compute_points = compute_points + 10 WHERE id = ?", (request.user['user_id'],))
        db.commit()
        new_points = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
        return jsonify({
            'code': 500,
            'message': error,
            'data': {
                'original_img': original_img_url,
                'task_id': task_id,
                'remaining_points': new_points['compute_points']
            }
        })
    else:
        log_api_call(request.user['user_id'], '2d_generation', params={'style_id': style_id}, status='success')
    
    # 如果成功，下载并保存生成的图片
    local_img_url, download_error = download_image_to_local(image_urls[0])
    if local_img_url:
        generated_img_url = local_img_url
    else:
        print(f"[WARN] 图片下载失败({download_error})，使用原URL")
        generated_img_url = image_urls[0]
    
    # 更新任务状态
    result_data = {'img': generated_img_url}
    if original_img_url:
        result_data['original_img'] = original_img_url
    db.execute("UPDATE tasks SET status = 'completed', result_data = ?, completed_at = datetime('now', '+8 hours') WHERE id = ?",
               (json.dumps(result_data), task_id))
    db.commit()
    
    new_points = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
    
    return jsonify({
        'code': 200,
        'data': {
            'img': generated_img_url,
            'original_img': original_img_url,
            'task_id': task_id,
            'remaining_points': new_points['compute_points']
        }
    })


@app.route('/api/generate/3d', methods=['POST'])
@require_auth
def generate_3d():
    data = request.json
    image_data = data.get('image', '')
    if not image_data:
        return jsonify({'code': 400, 'message': '请提供2D图像'}), 400
    db = get_db()
    user = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
    if not user or user['compute_points'] < 50:
        return jsonify({'code': 400, 'message': '算力点不足，需要50点'}), 400
    
    # 创建任务记录
    db.execute("INSERT INTO tasks (user_id, task_type, status, input_data, points_cost) VALUES (?, ?, ?, ?, ?)",
               (request.user['user_id'], '3d_generation', 'processing',
                json.dumps({'source': '2d_to_3d'}), 50))
    db.execute("UPDATE users SET compute_points = compute_points - 50 WHERE id = ?", (request.user['user_id'],))
    db.commit()
    
    # 保存输入图片用于显示
    img_url = save_base64_image(image_data, subfolder="library")
    task_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    try:
        # 调用Doubao-Seed3D API - 使用已保存的本地文件路径（避免前端canvas转换的base64格式问题）
        model_url, error = call_seed3d_api(img_url)
        
        if error:
            # API调用失败
            db.execute("UPDATE tasks SET status = 'failed', result_data = ?, error_message = ?, completed_at = datetime('now', '+8 hours') WHERE id = ?",
                      (json.dumps({'img': img_url}), error, task_id))
            db.commit()
            # 退还算力点
            db.execute("UPDATE users SET compute_points = compute_points + 50 WHERE id = ?", (request.user['user_id'],))
            db.commit()
            log_api_call(request.user['user_id'], '3d_generation', params={'source': '2d_to_3d'}, status='failed')
            new_points = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
            return jsonify({'code': 500, 'message': error, 'data': {'img': img_url, 'task_id': task_id, 'remaining_points': new_points['compute_points']}})
        
        # 生成预览图
        preview_url = generate_model_preview(model_url, task_id)
        
        # 更新任务状态
        result_data = {'img': img_url, 'model_url': model_url, 'model_format': 'glb', 'preview_url': preview_url}
        db.execute("UPDATE tasks SET status = 'completed', result_data = ?, completed_at = datetime('now', '+8 hours') WHERE id = ?",
                  (json.dumps(result_data), task_id))
        db.commit()
        
        # 记录API调用
        log_api_call(request.user['user_id'], '3d_generation', params={'source': '2d_to_3d'}, status='success')
        
        new_points = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
        return jsonify({
            'code': 200,
            'data': {
                'img': img_url,
                'model_url': model_url,
                'preview_url': preview_url,
                'task_id': task_id,
                'remaining_points': new_points['compute_points']
            }
        })
        
    except Exception as e:
        db.execute("UPDATE tasks SET status = 'failed', result_data = ?, error_message = ?, completed_at = datetime('now', '+8 hours') WHERE id = ?",
                  (json.dumps({'img': img_url}), str(e), task_id))
        db.commit()
        # 退还算力点
        db.execute("UPDATE users SET compute_points = compute_points + 50 WHERE id = ?", (request.user['user_id'],))
        db.commit()
        log_api_call(request.user['user_id'], '3d_generation', params={'source': '2d_to_3d'}, status='failed')
        new_points = db.execute("SELECT compute_points FROM users WHERE id = ?", (request.user['user_id'],)).fetchone()
        return jsonify({'code': 500, 'message': str(e), 'data': {'img': img_url, 'task_id': task_id, 'remaining_points': new_points['compute_points']}})


# ================= 从数据库读取API配置 =================
def get_api_config(api_id):
    try:
        db = get_db()
        config = db.execute("SELECT * FROM api_config WHERE id = ?", (api_id,)).fetchone()
        if config:
            return {
                'api_key': config['api_key'],
                'base_url': config['base_url'],
                'model_name': config['model_name']
            }
    except Exception as e:
        print(f"[ERROR] 读取API配置失败: {e}")
    # 回退到默认值 (请设置环境变量或在后台管理页面配置)
    if api_id == 'mimo':
        return {
            'api_key': os.environ.get('MIMO_API_KEY', ''),
            'base_url': 'https://token-plan-cn.xiaomimimo.com/v1',
            'model_name': 'mimo-v2.5'
        }
    elif api_id == 'jimo':
        return {
            'api_key': os.environ.get('JIMO_API_KEY', ''),
            'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
            'model_name': 'doubao-seedream-4-5-251128'
        }
    elif api_id == 'seed3d':
        return {
            'api_key': os.environ.get('SEED3D_API_KEY', ''),
            'base_url': 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
            'model_name': 'doubao-seed3d-2-0-260328'
        }
    return None


def upload_to_imgbb(image_data):
    """上传图片到ImgBB免费图床（有稳定API）"""
    try:
        import requests
        import os
        import base64
        import tempfile
        
        # ImgBB API密钥 (请到 https://api.imgbb.com/ 获取免费密钥)
        IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY', 'YOUR_IMGBB_API_KEY')
        
        print(f"[INFO] 正在上传图片到ImgBB图床...")
        
        # 处理输入数据
        upload_data = None
        if image_data.startswith('data:image'):
            # 已经是base64格式
            upload_data = image_data
            print(f"[INFO] 使用Base64格式上传")
        elif image_data.startswith('/'):
            # 本地文件路径
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), image_data.lstrip('/'))
            print(f"[INFO] 本地文件路径: {file_path}")
            if os.path.exists(file_path):
                # 读取文件并转换为base64
                with open(file_path, 'rb') as f:
                    import base64
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                    upload_data = f"data:image/png;base64,{encoded}"
            else:
                return None, "文件不存在"
        else:
            # 已经是URL
            return image_data, None
        
        if not upload_data:
            return None, "无法处理图片数据"
        
        # ImgBB API上传
        url = "https://api.imgbb.com/1/upload"
        
        payload = {
            'key': IMGBB_API_KEY,
            'image': upload_data.split(',')[1] if ',' in upload_data else upload_data  # 只传base64内容
        }
        
        response = requests.post(url, data=payload, timeout=30)
        
        print(f"[DEBUG] ImgBB响应状态码: {response.status_code}")
        print(f"[DEBUG] ImgBB响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and 'data' in result:
                img_url = result['data'].get('url')
                if img_url:
                    print(f"[OK] 图片上传成功！公网URL: {img_url}")
                    return img_url, None
        
        return None, "ImgBB上传失败"
        
    except Exception as e:
        print(f"[ERROR] 图片上传失败: {e}")
        import traceback
        traceback.print_exc()
        return None, f"图片上传失败: {e}"


def download_image_to_local(image_url, save_dir='static/uploads/library'):
    """下载远程图片到本地static目录"""
    try:
        import requests
        import uuid
        
        # 确保目录存在
        save_dir_full = os.path.join(os.path.dirname(os.path.abspath(__file__)), save_dir)
        os.makedirs(save_dir_full, exist_ok=True)
        
        # 生成唯一文件名
        ext = 'png'
        if '.' in image_url.split('?')[0]:
            ext = image_url.split('?')[0].split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                ext = 'png'
        
        filename = f"{uuid.uuid4().hex}.{ext}"
        save_path = os.path.join(save_dir_full, filename)
        
        print(f"[INFO] 正在下载远程图片: {image_url[:80]}...")
        
        # 下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(image_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        # 保存文件
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        local_path = f"/{save_dir}/{filename}"
        print(f"[OK] 图片下载到本地: {local_path}")
        return local_path, None
        
    except Exception as e:
        print(f"[ERROR] 图片下载失败: {e}")
        import traceback
        traceback.print_exc()
        return None, f"图片下载失败: {e}"


def call_seed3d_api(image_input):
    """调用Doubao-Seed3D API进行2D转3D"""
    config = get_api_config('seed3d')
    if not config or not config['api_key']:
        return None, '请在后台配置Doubao-Seed3D API Key'
    
    try:
        import requests
        from flask import request
        
        print(f"\n{'='*60}")
        print(f"[DEBUG] call_seed3d_api 开始执行")
        print(f"[DEBUG] 输入图片: {image_input[:100]}")
        print(f"{'='*60}")
        
        image_payload = None
        
        if image_input.startswith('http://') or image_input.startswith('https://'):
            image_payload = image_input
            print(f"[OK] 使用HTTP URL")
        elif image_input.startswith('/'):
            print(f"[INFO] 检测到本地路径，读取文件并转Base64")
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), image_input.lstrip('/'))
            if os.path.exists(file_path):
                import base64
                from PIL import Image as PILImage
                import io
                
                img = PILImage.open(file_path)
                w, h = img.size
                img_format = img.format
                print(f"[INFO] 原始图片尺寸: {w}x{h}, 模式: {img.mode}, 格式: {img_format}")
                
                # 统一缩放到 2048x2048 以内（减小base64体积，提高API兼容性）
                max_dim = 2048
                if w > max_dim or h > max_dim:
                    ratio = min(max_dim / w, max_dim / h)
                    new_w, new_h = int(w * ratio), int(h * ratio)
                    img = img.resize((new_w, new_h), PILImage.LANCZOS)
                    print(f"[INFO] 图片已缩放至: {new_w}x{new_h}")
                
                # 统一转换为 RGB JPEG 格式（体积小、兼容性好，避免RGBA PNG过大导致API拒绝）
                if img.mode in ('RGBA', 'P', 'LA', 'L'):
                    img = img.convert('RGB')
                
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=85)
                raw_bytes = buf.getvalue()
                file_size_mb = len(raw_bytes) / (1024 * 1024)
                print(f"[INFO] JPEG文件大小: {file_size_mb:.2f} MB")
                
                if file_size_mb > 8:
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=60)
                    raw_bytes = buf.getvalue()
                    file_size_mb = len(raw_bytes) / (1024 * 1024)
                    print(f"[INFO] 压缩后JPEG文件大小: {file_size_mb:.2f} MB")
                
                encoded = base64.b64encode(raw_bytes).decode('utf-8')
                image_payload = f"data:image/jpeg;base64,{encoded}"
                print(f"[OK] Base64转换完成，格式: JPEG，编码长度: {len(encoded)} 字符")
            else:
                return None, f"本地文件不存在: {file_path}"
        elif image_input.startswith('data:image'):
            print(f"[INFO] 检测到前端传入的Base64，转存为本地文件后处理")
            try:
                import base64 as b64
                from PIL import Image as PILImage
                import io
                
                header, encoded_data = image_input.split(',', 1)
                img_bytes = b64.b64decode(encoded_data)
                img = PILImage.open(io.BytesIO(img_bytes))
                w, h = img.size
                print(f"[INFO] Base64图片尺寸: {w}x{h}, 模式: {img.mode}")
                
                # 统一缩放到 2048x2048 以内
                max_dim = 2048
                if w > max_dim or h > max_dim:
                    ratio = min(max_dim / w, max_dim / h)
                    new_w, new_h = int(w * ratio), int(h * ratio)
                    img = img.resize((new_w, new_h), PILImage.LANCZOS)
                    print(f"[INFO] 图片已缩放至: {new_w}x{new_h}")
                
                # 统一转换为 RGB JPEG
                if img.mode in ('RGBA', 'P', 'LA', 'L'):
                    img = img.convert('RGB')
                
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=85)
                jpeg_bytes = buf.getvalue()
                
                if len(jpeg_bytes) / (1024 * 1024) > 8:
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=60)
                    jpeg_bytes = buf.getvalue()
                
                encoded = b64.b64encode(jpeg_bytes).decode('utf-8')
                image_payload = f"data:image/jpeg;base64,{encoded}"
                print(f"[OK] Base64转JPEG完成，编码长度: {len(encoded)} 字符")
            except Exception as conv_err:
                print(f"[WARN] Base64转换失败({conv_err})，直接使用原始数据")
                image_payload = image_input
        else:
            image_payload = image_input
            print(f"[INFO] 使用原始数据")
        
        if not image_payload:
            return None, "无法处理图片输入数据"
        
        print(f"[DEBUG] 最终图片载荷类型: {'URL' if image_payload.startswith('http') else 'Base64'}")
        print(f"[DEBUG] 最终图片载荷长度: {len(image_payload)} 字符")
        print(f"[DEBUG] 最终图片载荷前100字符: {image_payload[:100]}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }
        
        payload = {
            "model": config['model_name'],
            "content": [
                {
                    "type": "text",
                    "text": "--subdivisionlevel medium --fileformat glb"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_payload
                    }
                }
            ]
        }
        
        img_url_val = payload['content'][1]['image_url']['url']
        print(f"[DEBUG] payload.image_url长度: {len(img_url_val)}, 前缀: {img_url_val[:30]}")
        print(f"[DEBUG] model: {config['model_name']}, base_url: {config['base_url']}")
        
        # 创建任务
        print(f"[INFO] 正在调用Doubao-Seed3D-2.0 API创建任务...")
        
        import time
        max_retries = 3
        response = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(config['base_url'], headers=headers, json=payload, timeout=120)
                print(f"[DEBUG] API响应状态码: {response.status_code} (尝试 {attempt+1}/{max_retries})")
                print(f"[DEBUG] API响应内容: {response.text[:500]}")
                if response.status_code == 200:
                    break
                if attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 10
                    print(f"[WARN] API返回 {response.status_code}，{wait_sec}秒后重试...")
                    time.sleep(wait_sec)
            except Exception as req_err:
                last_error = req_err
                print(f"[ERROR] 请求异常 (尝试 {attempt+1}/{max_retries}): {type(req_err).__name__}: {req_err}")
                if attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 10
                    print(f"[WARN] {wait_sec}秒后重试...")
                    time.sleep(wait_sec)
        
        if response is None:
            return None, f'调用Doubao-Seed3D-2.0 API失败: {last_error}'
        if response.status_code != 200:
            return None, f'Doubao-Seed3D API请求失败 ({response.status_code}): {response.text}'
        result = response.json()
        
        task_id = result.get('id')
        if not task_id:
            print(f"[ERROR] API返回结果: {result}")
            return None, f'Doubao-Seed3D-2.0 API返回无效响应: {result}'
        
        print(f"[OK] 任务创建成功: {task_id}")
        
        # 轮询查询任务状态
        status_url = f"{config['base_url']}/{task_id}"
        max_wait = 1800  # 最多等待30分钟（3D模型生成需要较长时间）
        poll_interval = 15  # 每15秒查询一次
        waited = 0
        
        while waited < max_wait:
            print(f"[INFO] 查询任务状态 ({waited}/{max_wait}秒)...")
            status_response = requests.get(status_url, headers=headers, timeout=30)
            print(f"[DEBUG] 任务状态响应: {status_response.text[:300]}...")
            status_response.raise_for_status()
            status_result = status_response.json()
            
            task_status = status_result.get('status')
            print(f"[INFO] 任务状态: {task_status}")
            
            if task_status == 'succeeded':
                # 任务成功，获取模型文件URL
                print(f"[OK] 任务完成！")
                print(f"[DEBUG] 完整任务响应: {status_result}")
                
                # 解析真实的响应结构
                content_data = status_result.get('content', {})
                zip_url = content_data.get('file_url')
                
                if not zip_url:
                    return None, f'Doubao-Seed3D-2.0未返回模型文件，响应内容: {status_result}'
                
                print(f"[OK] 找到 ZIP 文件: {zip_url}")
                
                # 下载 ZIP 文件
                print(f"[INFO] 正在下载模型文件...")
                zip_response = requests.get(zip_url, timeout=120)
                zip_response.raise_for_status()
                
                # 保存到本地临时目录
                import io
                import zipfile
                from datetime import datetime
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                models_dir = os.path.join(UPLOAD_FOLDER, 'models')
                os.makedirs(models_dir, exist_ok=True)
                
                # 解压 ZIP
                zip_file = io.BytesIO(zip_response.content)
                glb_file_name = None
                glb_file_path = None
                
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    file_list = zf.namelist()
                    print(f"[INFO] ZIP 包含文件: {file_list}")
                    for f in file_list:
                        if f.lower().endswith('.glb'):
                            glb_file_name = f
                            # 解压到目标路径
                            target_name = f"model_{timestamp}.glb"
                            glb_file_path = os.path.join(models_dir, target_name)
                            with zf.open(f) as source, open(glb_file_path, 'wb') as target:
                                target.write(source.read())
                            break
                
                if not glb_file_path:
                    # 没有找到 GLB，直接把整个 ZIP 里的文件都解压
                    for f in file_list:
                        if f.lower().endswith('.obj') or f.lower().endswith('.gltf'):
                            glb_file_name = f
                            ext = os.path.splitext(f)[1]
                            target_name = f"model_{timestamp}{ext}"
                            glb_file_path = os.path.join(models_dir, target_name)
                            with zf.open(f) as source, open(glb_file_path, 'wb') as target:
                                target.write(source.read())
                            break
                
                if not glb_file_path:
                    return None, 'ZIP 中没有找到 .glb 或 .obj 模型文件'
                
                # 返回相对 URL，让前端可以直接访问
                model_url = f"/static/uploads/models/{target_name}"
                print(f"[OK] 模型已保存: {model_url}")
                return model_url, None
                
            elif task_status == 'failed':
                # 任务失败
                print(f"[ERROR] 任务失败: {status_result}")
                return None, f'Doubao-Seed3D-2.0任务执行失败: {status_result}'
            
            # 还在处理中
            print(f"[INFO] 任务状态: {task_status}，继续等待...")
            import time
            time.sleep(poll_interval)
            waited += poll_interval
        
        # 超时
        print(f"[ERROR] 任务超时，已等待 {max_wait} 秒")
        return None, f'Doubao-Seed3D-2.0任务执行超时（已等待{max_wait//60}分钟），请稍后重试'
        
    except Exception as e:
        import traceback
        error_msg = f"调用Doubao-Seed3D-2.0 API失败: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return None, error_msg


def call_mimo_api(messages, model="mimo-v2.5", temperature=0.7):
    """调用 Mimo V2.5 API"""
    config = get_api_config('mimo')
    if not config or not config['api_key']:
        return None, "请在后台配置 Mimo API Key"
    
    try:
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024
        }
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'], None
        else:
            return None, f"Mimo API 错误: {response.status_code} - {response.text}"
    except Exception as e:
        return None, f"调用 Mimo API 失败: {str(e)}"


def call_jimo_api(prompt, image_data=None, size="1728x2304", n=1):
    """调用即梦4.5 API进行文生图/图生图"""
    config = get_api_config('jimo')
    if not config or not config['api_key']:
        return None, "请在后台配置即梦 API Key"
    
    try:
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }
        
        data = {
            "model": config['model_name'],
            "prompt": prompt,
            "size": size,
            "n": n
        }
        
        # 图生图模式：传递参考图片
        if image_data:
            print(f"[INFO] 检测到图片输入，使用图生图模式")
            # 即梦API使用 image 参数传递参考图
            # 如果是base64格式，直接传递
            if image_data.startswith('data:'):
                data["image"] = image_data
                print(f"[INFO] 使用 base64 图片作为参考图")
            else:
                # 如果是URL格式
                data["image"] = image_data
                print(f"[INFO] 使用 URL 图片作为参考图")
        
        print(f"[INFO] 调用即梦API，提示词: {prompt[:100]}...")
        print(f"[INFO] 图片参数: {'有' if image_data else '无'}")
        print(f"[INFO] 请求尺寸: {size}")
        
        response = requests.post(
            f"{config['base_url']}/images/generations",
            headers=headers,
            json=data,
            timeout=120
        )
        
        print(f"[INFO] 即梦API响应状态码: {response.status_code}")
        print(f"[INFO] 即梦API响应内容: {response.text[:500]}...")
        
        if response.status_code == 200:
            result = response.json()
            image_urls = [item['url'] for item in result['data']]
            print(f"[OK] 即梦API调用成功，返回 {len(image_urls)} 张图片")
            return image_urls, None
        else:
            error_msg = f"即梦API 错误: {response.status_code} - {response.text}"
            print(f"[ERROR] {error_msg}")
            return None, error_msg
    except Exception as e:
        import traceback
        error_msg = f"调用即梦API失败: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return None, error_msg


@app.route('/api/agent/chat', methods=['POST'])
@require_auth
def agent_chat():
    data = request.json
    message = data.get('message', '')
    context = data.get('context', {})
    
    if not message:
        return jsonify({'code': 400, 'message': '请输入消息'}), 400
    
    # ================= Agent 系统提示词 =================
    system_prompt = """你是 AI 手办设计平台的智能助手 Agent，你的职责是：
1. 分析用户的需求，理解他们想要对素材进行什么操作
2. 提供清晰、友好、有帮助的回答
3. 如果用户提到"编辑"、"重新编辑"，告诉他们可以用工具栏的按钮
4. 如果用户提到"3D"、"三维"，告诉他们已经准备好了 3D 重建管线
5. 如果用户提到"去背景"，告诉他们正在调用分割算法
6. 保持回答简洁明了，在 2 句话以内

你的语气友好、专业，像一个贴心的创意助手。"""
    
    # 构建消息列表
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    # 检查是否配置了 Mimo API
    mimo_config = get_api_config('mimo')
    
    if not mimo_config or not mimo_config['api_key']:
        # 如果没有配置 API Key，使用关键词匹配
        reply = f"已收到您的指令：「{message}」。Agent 正在分析上下文并准备执行操作。"
        if 'reedit' in message.lower() or '编辑' in message:
            reply = "好的，我已将该素材设为 Control 图。请上传 Target 图或输入文本描述，我将执行 AI Edit 结构转换。"
        elif '3d' in message.lower() or '三维' in message:
            reply = "正在准备 3D 重建管线。请确认素材已就绪，系统将调用 AI 底层服务进行结构提取。"
        elif '去背景' in message or 'remove' in message.lower():
            reply = "正在调用分割算法进行背景剥离处理..."
    else:
        # 调用 Mimo API
        reply, error = call_mimo_api(messages)
        if error:
            reply = f"Agent 暂时无法响应：{error}"
    
    return jsonify({
        'code': 200,
        'data': {
            'reply': reply,
            'context': context
        }
    })


# ================= 管理员登录API =================
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'code': 400, 'message': '请输入用户名和密码'}), 400
    
    db = get_db()
    admin = db.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    if not admin:
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
    
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    if pw_hash != admin['password_hash']:
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
    
    token = generate_token(admin['id'], admin['username'], 'admin')
    return jsonify({'code': 200, 'data': {'token': token, 'username': admin['username']}})


# ================= 风格管理API =================
@app.route('/api/admin/styles', methods=['GET'])
@require_admin
def admin_get_styles():
    db = get_db()
    cursor = db.execute("SELECT * FROM styles ORDER BY sort_order ASC, id ASC")
    styles = [dict(row) for row in cursor.fetchall()]
    return jsonify({'code': 200, 'data': styles})


@app.route('/api/admin/styles', methods=['POST'])
@require_admin
def admin_create_style():
    data = request.json
    style_id = data.get('id', '')
    name = data.get('name', '')
    prompt = data.get('prompt', '')
    img_base64 = data.get('img', '')
    
    if not style_id or not name or not prompt:
        return jsonify({'code': 400, 'message': '请填写完整信息'}), 400
    
    img_url = save_base64_image(img_base64, 'styles')
    
    db = get_db()
    max_order = db.execute("SELECT MAX(sort_order) as max_order FROM styles").fetchone()
    new_order = (max_order['max_order'] or 0) + 1
    db.execute("INSERT INTO styles (id, name, prompt, img, sort_order) VALUES (?, ?, ?, ?, ?)",
               (style_id, name, prompt, img_url, new_order))
    db.commit()
    return jsonify({'code': 200, 'message': '创建成功'})


@app.route('/api/admin/styles/<style_id>', methods=['PUT'])
@require_admin
def admin_update_style(style_id):
    data = request.json
    name = data.get('name')
    prompt = data.get('prompt')
    img_base64 = data.get('img')
    
    db = get_db()
    existing = db.execute("SELECT * FROM styles WHERE id = ?", (style_id,)).fetchone()
    if not existing:
        return jsonify({'code': 404, 'message': '风格不存在'}), 404
    
    update_fields = []
    update_values = []
    
    if name is not None:
        update_fields.append("name = ?")
        update_values.append(name)
    if prompt is not None:
        update_fields.append("prompt = ?")
        update_values.append(prompt)
    if img_base64 is not None:
        img_url = save_base64_image(img_base64, 'styles')
        update_fields.append("img = ?")
        update_values.append(img_url)
    
    if update_fields:
        update_values.append(style_id)
        db.execute(f"UPDATE styles SET {', '.join(update_fields)} WHERE id = ?", update_values)
        db.commit()
    
    return jsonify({'code': 200, 'message': '更新成功'})


@app.route('/api/admin/styles/<style_id>', methods=['DELETE'])
@require_admin
def admin_delete_style(style_id):
    db = get_db()
    db.execute("DELETE FROM styles WHERE id = ?", (style_id,))
    db.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


# ================= 灵感素材管理API =================
@app.route('/api/admin/inspirations', methods=['GET'])
@require_admin
def admin_get_inspirations():
    db = get_db()
    cursor = db.execute("SELECT * FROM inspirations ORDER BY created_at DESC")
    inspirations = [dict(row) for row in cursor.fetchall()]
    return jsonify({'code': 200, 'data': inspirations})


@app.route('/api/admin/inspirations', methods=['POST'])
@require_admin
def admin_create_inspiration():
    data = request.json
    title = data.get('title', '') or '精选灵感素材'
    content = data.get('content', '') or ''
    img_base64 = data.get('img', '')
    
    if not img_base64:
        return jsonify({'code': 400, 'message': '请上传图片'}), 400
    
    img_url = save_base64_image(img_base64, 'inspirations')
    
    db = get_db()
    cursor = db.execute("INSERT INTO inspirations (title, content, img) VALUES (?, ?, ?)",
                        (title, content, img_url))
    db.commit()
    return jsonify({'code': 200, 'message': '创建成功', 'data': {'id': cursor.lastrowid}})


@app.route('/api/admin/inspirations/<int:insp_id>', methods=['PUT'])
@require_admin
def admin_update_inspiration(insp_id):
    data = request.json
    title = data.get('title')
    content = data.get('content')
    img_base64 = data.get('img')
    
    db = get_db()
    existing = db.execute("SELECT * FROM inspirations WHERE id = ?", (insp_id,)).fetchone()
    if not existing:
        return jsonify({'code': 404, 'message': '灵感不存在'}), 404
    
    update_fields = []
    update_values = []
    
    if title is not None:
        update_fields.append("title = ?")
        update_values.append(title)
    if content is not None:
        update_fields.append("content = ?")
        update_values.append(content)
    if img_base64 is not None:
        img_url = save_base64_image(img_base64, 'inspirations')
        update_fields.append("img = ?")
        update_values.append(img_url)
    
    if update_fields:
        update_values.append(insp_id)
        db.execute(f"UPDATE inspirations SET {', '.join(update_fields)} WHERE id = ?", update_values)
        db.commit()
    
    return jsonify({'code': 200, 'message': '更新成功'})


@app.route('/api/admin/inspirations/<int:insp_id>', methods=['DELETE'])
@require_admin
def admin_delete_inspiration(insp_id):
    db = get_db()
    db.execute("DELETE FROM inspirations WHERE id = ?", (insp_id,))
    db.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


if __name__ == '__main__':
    init_db()
    print("[OK] AI手办设计平台后端服务已启动！")
    print("[INFO] 请在浏览器访问: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
