# Design: 多用户认证体系

## 认证方案：双 Token JWT（Access + Refresh）

- **Access Token**：JWT，有效期 15 分钟，自包含
- **Refresh Token**：随机字符串，有效期 7 天，存 MongoDB，支持轮换/撤销

## 数据流

```
send-code:  手机号 → 生成6位码 → 存MongoDB(TTL 5min) → 返回成功
login:      手机号+验证码 → 验证 → 查/建User → 签发Token → 返回
业务请求:    Authorization: Bearer <token> → 中间件解码 → request.state.user_id → 路由使用
refresh:    旧RefreshToken → 验证 → 失效旧 → 签发新Access+新Refresh
logout:     失效当前用户所有RefreshToken
```

## 配置

```python
JWT_SECRET = "从环境变量获取"       # HS256 密钥
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
SMS_MOCK = True                    # True=固定123456, False=真实短信
SMS_RESEND_INTERVAL = 60           # 秒
SMS_CODE_EXPIRE = 300              # 秒
```

## JWT Payload

```json
{"sub": "user_id", "phone": "138xxxx1234", "iat": ..., "exp": ...}
```

## 统一响应格式

```python
class APIResponse(BaseModel):
    code: int = 0        # 0=成功, 1xxx=认证错误, 2xxx=鉴权错误
    message: str = "ok"
    data: Any = None
```

错误码：1001(手机号不合法) 1002(发送频繁) 1003(验证码错误) 1004(验证码过期) 2001(未登录) 2002(Token过期) 2003(Token无效) 2004(Refresh失效)

## 鉴权中间件

```python
async def get_current_user(
    authorization: str = Header(None)
) -> dict:
    # 1. 从 /api/v1/auth/*, /health, /config/amap 跳过
    # 2. 提取 Bearer token
    # 3. 解码 JWT
    # 4. 注入 request.state.user_id
    # 5. 返回 user 或抛业务错误
```

## 数据库索引

- `verification_codes._id` — phone 作为主键（唯一）
- `verification_codes.expires_at` — TTL 索引（MongoDB 自动过期）
- `refresh_tokens.token` — 唯一索引
- `refresh_tokens.user_id` — 普通索引
- `refresh_tokens.expires_at` — TTL 索引
