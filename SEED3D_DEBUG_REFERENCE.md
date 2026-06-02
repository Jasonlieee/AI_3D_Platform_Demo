# Seed3D API Debug Reference

## 问题概述

Seed3D API (`doubao-seed3d-2-0-260328`) 持续返回 400 InvalidParameter 错误：
```
"content[1].image_url" specified in the request is not valid
```

## 根因

**Python 浅拷贝导致 payload 数据被 debug 代码破坏。**

在 `call_seed3d_api` 函数中，有一段 debug 代码用于打印日志：
```python
debug_payload = payload.copy()  # BUG: 浅拷贝！
debug_payload['content'][i]['image_url']['url'] = '<base64 image, length=...>'
```

`dict.copy()` 是**浅拷贝**，嵌套的 `content` 列表和字典与原始 `payload` 共享同一对象。
修改 `debug_payload` 的同时，`payload` 中的 base64 图片数据也被替换成了占位符文本，
导致发给 API 的 `image_url` 不是 `data:image/jpeg;base64,/9j/4AAQ...` 而是 `<base64 image, length=375319>`。

## 修复方案

删除有问题的 debug 代码，改为安全的日志方式（只读取不修改）：
```python
img_url_val = payload['content'][1]['image_url']['url']
print(f"[DEBUG] payload.image_url长度: {len(img_url_val)}, 前缀: {img_url_val[:30]}")
print(f"[DEBUG] model: {config['model_name']}, base_url: {config['base_url']}")
```

## 正确的 API 调用格式

### API 配置
- base_url: `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`
- model_name: `doubao-seed3d-2-0-260328`
- api_key: `ark-xxxx` (Bearer Token)

### 请求格式
```json
{
    "model": "doubao-seed3d-2-0-260328",
    "content": [
        {"type": "text", "text": "--subdivisionlevel medium --fileformat glb"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ..."}}
    ]
}
```

### 图片要求
- 格式: JPEG (统一转换，兼容性最好)
- 尺寸: <= 2048x2048 (超过自动缩放)
- 大小: < 10MB
- 模式: RGB (RGBA/PLA/L 自动转换)
- Base64 前缀: `data:image/jpeg;base64,`

### 成功响应
```json
{"id": "cgt-20260531111712-twjqs"}
```

## 排查清单

如果再次出现 400 错误，按以下顺序排查：

1. **检查 payload 是否被破坏**
   - 在 `requests.post` 前打印 `len(payload['content'][1]['image_url']['url'])`
   - 正常应为 40万+ 字符（JPEG base64）
   - 如果只有几十~几百字符，说明 payload 被修改了

2. **检查图片格式**
   - 必须是 `data:image/jpeg;base64,` 开头
   - 文件头 hex 应为 `ffd8ffe0` (JPEG magic number)

3. **检查 API 配置**
   - model_name: `doubao-seed3d-2-0-260328`
   - base_url: `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`
   - api_key 有效且有权限

4. **检查图片尺寸和大小**
   - 宽高 <= 4096px (推荐 <= 2048px)
   - 文件 < 10MB

## 测试验证方法

用独立脚本测试 API 是否正常：
```python
import requests, json, base64
from PIL import Image
import io

img = Image.open('test.png').convert('RGB')
buf = io.BytesIO()
img.save(buf, format='JPEG', quality=85)
b64 = base64.b64encode(buf.getvalue()).decode()

r = requests.post(
    'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
    headers={"Content-Type": "application/json", "Authorization": "Bearer <key>"},
    json={
        "model": "doubao-seed3d-2-0-260328",
        "content": [
            {"type": "text", "text": "--subdivisionlevel medium --fileformat glb"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]
    },
    timeout=60
)
print(r.status_code, r.text)
```

## 关键教训

**Python `dict.copy()` 是浅拷贝！** 嵌套对象（列表、字典）仍然共享引用。
需要深拷贝时使用 `import copy; copy.deepcopy(obj)`，或者根本不要修改原始数据的副本。

## 修复日期

2026-05-31
