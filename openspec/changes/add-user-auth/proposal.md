# Proposal: 增加多用户认证体系

## 动机

当前项目**零认证**。33 个 API 端点完全开放，`user_id` 仅作为客户端传入的任意字符串（iOS 硬编码为 `"ios_user"`）。无法区分不同用户的收藏路线、搜索历史、个人偏好等。任何人均可伪造他人身份访问/修改数据。

## 变更内容

### 后端（新增 4 个认证端点 + 1 个全局中间件）

1. **`POST /api/v1/auth/send-code`** — 发送短信验证码（Mock：固定 `123456`，打印日志）
2. **`POST /api/v1/auth/login`** — 验证码登录，返回 Access Token + Refresh Token
3. **`POST /api/v1/auth/refresh`** — Refresh Token 换新 Access Token（轮换制）
4. **`POST /api/v1/auth/logout`** — 登出，失效 Refresh Token
5. **JWT 鉴权中间件** — 全局拦截业务接口，从 `Authorization: Bearer` 提取并验证 JWT

### 统一响应格式

所有接口统一为 `{"code": 0, "message": "ok", "data": {...}}`。业务错误通过 code 区分，HTTP 状态码始终 200。

### 现有接口适配

30+ 业务接口从查询参数/路径取 `user_id` → 从 `request.state.user_id`（由中间件注入 JWT 中的 sub 字段）。

## 影响范围

- **破坏性变更**：响应格式从 `{"success": true, ...}` 改为 `{"code": 0, "message": "ok", "data": {...}}`。iOS 客户端需适配。
- **iOS 本次不改**，后续单独处理。
- 认证端点自身和 `/health`、`/config/amap` 不鉴权。

## 涉及文件

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `app/api/auth.py` | 认证路由 |
| 新增 | `app/schemas/auth.py` | 认证 Schema |
| 新增 | `app/services/auth_service.py` | Token 签发/验证、验证码管理 |
| 新增 | `app/middleware/auth.py` | JWT 鉴权中间件 |
| 新增 | `app/models/token.py` | RefreshToken MongoDB 文档 |
| 修改 | `app/main.py` | 注册路由和中间件 |
| 修改 | `app/config.py` | JWT_SECRET 等配置 |
| 修改 | `app/models/user.py` | phone 改为必填 |
| 修改 | `app/api/*.py` | user_id 来源改为 request.state |
| 修改 | `app/database.py` | 验证码 TTL 索引 |
