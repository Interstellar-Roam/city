# Tasks: 多用户认证体系

## Task 1: 配置 & 数据模型
- `app/config.py` — 新增 JWT 相关配置
- `app/models/user.py` — phone 必填，新增 is_active
- `app/models/token.py` — 新增 RefreshToken、VerificationCode 模型

## Task 2: 统一响应格式
- `app/schemas/common.py` — APIResponse schema
- 所有现有路由适配新格式

## Task 3: 认证服务
- `app/services/auth_service.py` — 验证码管理、Token 签发/验证/轮换
- `app/database.py` — 新增集合索引

## Task 4: 认证路由
- `app/schemas/auth.py` — 认证请求/响应 Schema
- `app/api/auth.py` — /api/v1/auth/* 四个端点

## Task 5: JWT 鉴权中间件
- `app/middleware/auth.py` — 全局 Bearer Token 验证
- `app/main.py` — 注册中间件

## Task 6: 现有接口适配
- 修改所有路由，user_id 从 request.state 获取
- 响应格式统一为 APIResponse

## Task 7: 测试 & 归档
- 全量测试
- OpenSpec 归档
