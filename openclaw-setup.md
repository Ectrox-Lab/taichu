# OpenClaw Feishu 集成部署文档 - 完整故障排查记录

## 项目概述

将 GPT-OSS-120B 模型通过 Flask 接入飞书机器人，实现群聊/私聊自动回复功能。

## 系统架构

```
飞书用户消息
    ↓
飞书服务器（国内）
    ↓ (HTTPS/Webhook)
内网穿透工具 / 公网IP
    ↓
台湾服务器 (192.168.88.253)
    ↓ (HTTP)
Flask 应用 (端口 9000)
    ↓ (HTTP)
120B 模型 API (端口 8005)
    ↓
AI 生成回复
    ↓
飞书消息发送 API
    ↓
飞书用户收到回复
```

## 服务器信息

| 项目 | 值 |
|------|-----|
| 服务器位置 | 台湾 |
| 内网 IP | 192.168.88.253 |
| 公网 IP | 1.34.114.26 |
| 操作系统 | Ubuntu 22.04 |
| SSH 端口 | 2222 |
| 用户名 | admin |

## 组件状态

### 1. Flask 应用 (feishu_webhook_debug.py)
- **状态**: ✅ 运行正常
- **监听**: 0.0.0.0:9000
- **功能**: 接收飞书 webhook，调用 120B 模型，回复消息
- **位置**: `/home/admin/feishu_webhook_debug.py`

### 2. 120B 模型 (Docker)
- **容器名**: atlas-core-120b-pp3
- **状态**: ✅ 运行正常
- **API 地址**: http://192.168.88.253:8005/v1/chat/completions
- **配置**: PP=3, GPUs 0,1,2

### 3. Cloudflare Tunnel
- **状态**: ✅ 运行但连接不稳定
- **隧道 ID**: 20e706f4-dcd2-460e-b777-d34232da678c
- **问题**: 飞书服务器无法连接

## 网络配置

### 端口开放情况

| 端口 | 服务 | 本地访问 | 公网直接访问 | 飞书访问 |
|------|------|---------|-------------|---------|
| 80 | HTTP/Nginx | ✅ | ✅ 但返回404 | ❌ 超时 |
| 8000 | Flask (iptables重定向) | ✅ | ✅ 正常 | ❌ 超时 |
| 443 | SSH | ✅ | ❌ 阻塞 | - |
| 9000 | Flask 直接 | ✅ | ❌ 仅内网 | - |
| 8005 | 120B模型 | ✅ | ❌ 仅内网 | - |

### iptables 规则
```
Chain PREROUTING (policy ACCEPT)
  REDIRECT   tcp  --  anywhere  anywhere  tcp dpt:8000 redir ports 9000
```

## 飞书应用配置

### 基本信息
- **App ID**: cli_a911066ad3b85bca
- **App Secret**: 5B12qyvp4DZuQ4c9UdLjwcEQxfSQ0BD7
- **应用名称**: Atlas-AI

### 已订阅事件
- ✅ im.message.receive_v1 (接收消息)
- ✅ im.chat.access_event.bot_p2p_chat_entered_v1 (用户进入会话)
- ✅ im.chat.member.bot.added_v1 (机器人进群)
- ✅ im.chat.member.bot.deleted_v1 (机器人被移出群)
- ✅ im.message.message_read_v1 (消息已读)
- ✅ im.message.recalled_v1 (消息撤回)

### 所需权限（已开通）
- ✅ 读取用户发给机器人的单聊消息
- ✅ 接收群聊中@机器人消息事件
- ✅ 获取单聊、群组消息
- ✅ 获取与发送单聊、群组消息
- ✅ 以应用的身份发消息
- ✅ 获取群组信息

### 版本状态
- **当前版本**: 已发布
- **Webhook URL**: 已配置（多次变更）

## 问题排查记录

### 问题 1: 端口 28000 被云服务商阻塞
**现象**: 
- 配置 Nginx 监听 28000 端口
- 本地访问正常
- 公网 `curl http://1.34.114.26:28000` 返回 "Connection refused"

**分析**: 
- 云服务商防火墙未开放 28000 端口
- 仅有 80 端口对外开放

**结论**: 放弃 28000 端口方案

---

### 问题 2: Cloudflare Tunnel 不稳定
**现象**:
- 配置 `feishu-tunnel.atlas-ai.tw` 指向 Cloudflare Tunnel
- 本地测试 HTTPS 访问正常
- Challenge 验证通过
- **飞书真实消息始终无法到达服务器**

**分析**:
- Cloudflare 隧道连接正常
- 日志显示隧道连接有重试、断开
- 可能是 Cloudflare 与飞书服务器之间的网络问题

**尝试**:
- 多次重启隧道
- 更换 tunnel 配置
- 问题依旧

**结论**: Cloudflare Tunnel 不适合此场景

---

### 问题 3: 80 端口被中间层拦截
**现象**:
- 配置 Nginx 80 端口代理到 Flask
- 本地 `curl http://127.0.0.1:80/webhook/feishu` 正常
- 公网 `curl http://1.34.114.26/webhook/feishu` 返回 404

**分析**:
- 公网 80 端口有另一层代理/负载均衡
- 不是直接连接到 Nginx

**结论**: 80 端口也无法使用

---

### 问题 4: 8000 端口部分可用
**现象**:
- 配置 iptables 8000 → 9000 重定向
- 本地访问: ✅ 正常
- 公网直接访问: ✅ 正常 (`curl http://1.34.114.26:8000/webhook/feishu` 返回 200)
- **飞书服务器访问: ❌ 超时 (3秒超时)**

**关键分析**:
```bash
# 本地测试
 curl http://192.168.88.253:8000/webhook/feishu
 {"status":"ok"}

# 公网直接测试（从其他服务器）
 curl http://1.34.114.26:8000/webhook/feishu
 {"status":"ok"}

# 飞书后台验证
 请求3秒超时
```

**可能原因**:
1. **云服务商防火墙限制了特定来源 IP**（如飞书服务器 IP 段）
2. **飞书服务器在境外**，与台湾服务器网络路由不通
3. **安全组规则**限制了入站来源
4. **地理位置问题**: 台湾服务器 ↔ 国内飞书服务器网络不通

---

### 问题 5: localtunnel 国内认证失败
**现象**:
- 服务器下载 NATAPP 客户端成功
- 运行后报错: `连接认证服务器错误`
- `Post "https://auth.natapp.cn/auth": context deadline exceeded`

**分析**:
- 台湾服务器到国内 NATAPP 认证服务器网络不通
- 可能是跨境网络问题

---

### 问题 6: ngrok 免费版需要 token
**现象**:
- 安装 ngrok 成功
- 启动报错: `authentication failed: Usage of ngrok requires a verified account and authtoken`

**分析**:
- ngrok 免费版也需要注册获取 token
- 国际版付款方式受限

---

## 当前有效的配置

### Flask 代码
- 文件: `/home/admin/feishu_webhook_debug.py`
- 监听: `0.0.0.0:9000`
- 功能完整: 支持私聊(p2p)和群聊(group)回复

### 120B 模型
- 容器运行正常
- API 可访问

### 直接访问地址（公网可访问）
```
http://1.34.114.26:8000/webhook/feishu
```
- 本地测试: ✅ 正常
- 公网测试: ✅ 正常
- 飞书访问: ❌ 超时

## 已验证的功能

| 功能 | 本地测试 | 公网直接测试 | 飞书真实请求 |
|------|---------|-------------|-------------|
| GET /webhook/feishu | ✅ | ✅ | - |
| POST Challenge | ✅ | ✅ | - |
| POST 消息事件 | ✅ | ✅ | ❌ 未到达 |
| AI 回复生成 | ✅ | ✅ | - |
| 发送消息到飞书 | ✅ (假ID失败) | - | - |

## 可能的解决方案

### 方案 1: 联系服务器提供商（推荐先尝试）
**操作**:
1. 联系台湾服务器提供商
2. 询问 8000 端口是否有入站 IP 限制
3. 询问是否有防火墙/安全组规则限制
4. 请求开放端口或添加飞书服务器 IP 白名单

**可行性**: ⭐⭐⭐⭐⭐（如果提供商配合）

---

### 方案 2: Windows 本地运行（绕过服务器）
**操作**:
1. Windows 电脑安装 Python
2. 复制 `feishu_webhook_debug.py` 到本地
3. 修改 MODEL_API 指向台湾服务器的 120B 模型
4. 本地运行 NATAPP 获取公网 URL
5. 飞书配置指向本地 NATAPP URL

**缺点**:
- Windows 电脑需要一直开机
- 依赖本地网络稳定

**可行性**: ⭐⭐⭐⭐

---

### 方案 3: 购买国内服务器（最稳定）
**推荐**:
- 阿里云 ECS（最低配置 1核1G，约 60元/月）
- 腾讯云 CVM
- 华为云

**优势**:
- 有公网 IP
- 直接配置安全组开放端口
- 无需内网穿透
- 国内网络 ↔ 飞书 连通性好

**可行性**: ⭐⭐⭐⭐⭐

---

### 方案 4: SSH 反向隧道（需要国内中转）
**前提**: 需要一台国内服务器作为中转

**操作**:
```bash
# 在台湾服务器上建立反向隧道到国内服务器
ssh -R 9000:localhost:9000 user@国内服务器IP

# 国内服务器配置 Nginx 或直接用端口
```

**可行性**: ⭐⭐⭐（需要额外资源）

---

### 方案 5: 使用飞书「长连接」方式
**操作**:
- 飞书后台选择「使用长连接接收事件」
- 建立 WebSocket 连接到飞书服务器
- 不需要公网 IP

**缺点**:
- 需要保持长连接
- 代码需要大幅修改

**可行性**: ⭐⭐

## 关键日志位置

```
/tmp/feishu-debug.log          # Flask 应用日志
/tmp/cloudflared.log           # Cloudflare 隧道日志
/tmp/localtunnel.log           # localtunnel 日志
/tmp/flask_stdout.log          # Flask 标准输出
/var/log/nginx/atlas-ai-*.log  # Nginx 日志
```

## 相关文件

```
/home/admin/feishu_webhook_debug.py          # Flask 主程序
/home/admin/.cloudflared/config.yml          # Cloudflare 配置
/etc/nginx/sites-enabled/atlas-ai            # Nginx 配置
/home/admin/国内内网穿透方案.md              # 内网穿透方案文档
```

## 飞书相关链接

- 开发者后台: https://open.feishu.cn/app/cli_a911066ad3b85bca/baseinfo
- 事件配置: https://open.feishu.cn/app/cli_a911066ad3b85bca/event
- 版本管理: https://open.feishu.cn/app/cli_a911066ad3b85bca/version
- 日志检索: https://open.feishu.cn/app/cli_a911066ad3b85bca/log

## 总结

**服务器端配置完全正确**，所有组件运行正常。

**核心问题**: 台湾服务器 ↔ 飞书服务器（国内）网络不通，可能是：
1. 云服务商防火墙限制
2. 跨境网络路由问题
3. IP 白名单限制

**需要解决**: 让飞书服务器能够访问到 `http://1.34.114.26:8000/webhook/feishu`

---

**最后更新**: 2026-02-23
