import sqlite3
import os

DB_FILE = 'app.db'

db = sqlite3.connect(DB_FILE)
cursor = db.cursor()

# 插入或更新国风风格
cursor.execute("""
    INSERT OR REPLACE INTO styles (id, name, prompt, img) 
    VALUES (?, ?, ?, ?)
""", (
    'guofeng', 
    '国风手办', 
    '基于真人照片转化为国风潮玩手办 IP 形象，从头到脚完整全身立绘，画面完整包含头部、躯干、四肢、双脚，无画面裁切，严格遵循标准 2:3Q 版头身比例，头大身小，躯干短而紧凑，手掌短小圆润，手部长度不超过胯部，杜绝过长、畸形手部，四肢与腿部比例均衡协调；完整提取原图人物发型、五官轮廓、国风传统服饰核心特征并保留，古风新中式汉服，精致传统刺绣纹样，真实古风布料哑光肌理；泡泡玛特黏土软胶手办质感，细腻哑光黏土肌理，柔和暖调商业柔光，人物带有自然腮红，皮克斯风格的美式3d动漫五官；全身正视图，构图端正，白色纯色极简背景，画面干净高级，超高清 8K，细节丰富细腻，真人五官柔和卡通化处理，全身上下比例统一协调', 
    ''
))

db.commit()

print("检查所有风格...")
cursor.execute("SELECT id, name FROM styles")
for row in cursor.fetchall():
    print(f"  - {row[0]}: {row[1]}")

db.close()
print("完成！")
