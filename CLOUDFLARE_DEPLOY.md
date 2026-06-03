# Cloudflare Tunnel 部署指南

## 前置条件

1. **注册域名** - 在 [Cloudflare](https://www.cloudflare.com/products/registrar/) 或其他域名注册商购买域名
2. **Cloudflare 账号** - 注册 [Cloudflare](https://dash.cloudflare.com/sign-up) 账号

## 部署步骤

### 步骤 1：添加域名到 Cloudflare

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 点击 "Add a Site"
3. 输入你的域名，选择 Free 计划
4. 按照提示修改域名的 Nameserver 为 Cloudflare 提供的地址
5. 等待 DNS 生效（通常需要几分钟到几小时）

### 步骤 2：安装 cloudflared 客户端

**Windows (推荐使用 PowerShell)：**

```powershell
# 方法1：使用 winget（推荐）
winget install Cloudflare.cloudflared

# 方法2：手动下载
# 访问 https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/local/
# 下载 Windows 64-bit 版本
```

**或者使用 Chocolatey：**
```powershell
choco install cloudflared
```

### 步骤 3：登录 Cloudflare

```powershell
cloudflared tunnel login
```

这会打开浏览器，让你选择要授权的域名。

### 步骤 4：创建命名隧道

```powershell
cloudflared tunnel create ai-3d-platform
```

记录返回的 Tunnel ID。

### 步骤 5：配置隧道

创建配置文件 `%USERPROFILE%\.cloudflared\config.yml`：

```yaml
tunnel: <TUNNEL_ID>
credentials-file: C:\Users\你的用户名\.cloudflared\<TUNNEL_ID>.json

ingress:
  - hostname: 你的域名.com
    service: http://localhost:5000
  - hostname: www.你的域名.com
    service: http://localhost:5000
  - service: http_status:404
```

### 步骤 6：配置 DNS 记录

```powershell
cloudflared tunnel route dns ai-3d-platform 你的域名.com
cloudflared tunnel route dns ai-3d-platform www.你的域名.com
```

### 步骤 7：启动隧道

```powershell
cloudflared tunnel run ai-3d-platform
```

### 步骤 8：启动 Flask 服务

在另一个终端窗口：
```powershell
python app.py
```

## 一键启动脚本

运行 `启动Cloudflare隧道.bat` 脚本，它会自动启动隧道和 Flask 服务。

## 注意事项

1. **首次启动需要登录** - cloudflared 会打开浏览器让你授权
2. **隧道名称** - 建议使用 `ai-3d-platform`，也可以自定义
3. **端口** - 确保 Flask 运行在 5000 端口
4. **防火墙** - 确保本地防火墙允许 cloudflared 访问

## 验证部署

1. 访问 `https://你的域名.com` 查看是否正常
2. 检查 HTTPS 证书是否自动配置
3. 测试 API 功能是否正常

## 常见问题

**Q: 隧道启动失败？**
A: 检查是否已登录 cloudflared，运行 `cloudflared tunnel login`

**Q: 域名无法访问？**
A: 检查 DNS 记录是否正确，运行 `cloudflared tunnel route dns` 重新配置

**Q: 如何停止隧道？**
A: 在隧道终端按 Ctrl+C，或运行 `cloudflared tunnel delete ai-3d-platform`

## 服务状态检查

```powershell
# 查看隧道列表
cloudflared tunnel list

# 查看隧道详情
cloudflared tunnel info ai-3d-platform
```
