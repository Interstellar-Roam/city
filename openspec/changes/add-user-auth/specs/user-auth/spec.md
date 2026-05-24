# User Auth Spec

## Requirements

### REQ-1: 发送短信验证码
系统应支持向指定手机号发送 6 位数字验证码（Mock 模式固定为 `123456`），验证码 5 分钟有效，60 秒内不可重复发送。

#### Scenario: 正常发送
- GIVEN 一个合法的 11 位手机号
- WHEN 调用 POST /api/v1/auth/send-code
- THEN 返回 code=0，data 包含 expires_in=300

#### Scenario: 手机号格式不合法
- GIVEN 一个非 11 位数字的手机号
- WHEN 调用 POST /api/v1/auth/send-code
- THEN 返回 code=1001

#### Scenario: 发送过于频繁
- GIVEN 60 秒内已发送过验证码
- WHEN 再次调用 POST /api/v1/auth/send-code
- THEN 返回 code=1002

### REQ-2: 验证码登录
系统应支持通过手机号+验证码登录，首次登录自动创建用户，返回双 Token。

#### Scenario: 正常登录
- GIVEN 已发送验证码到手机号
- WHEN 调用 POST /api/v1/auth/login 提供正确验证码
- THEN 返回 code=0，data 包含 access_token、refresh_token、user 对象

#### Scenario: 验证码错误
- GIVEN 验证码不匹配
- WHEN 调用 POST /api/v1/auth/login
- THEN 返回 code=1003

#### Scenario: 验证码过期
- GIVEN 验证码已超过 5 分钟
- WHEN 调用 POST /api/v1/auth/login
- THEN 返回 code=1004

### REQ-3: Token 刷新
系统应支持用 Refresh Token 换新 Access Token + 新 Refresh Token（轮换制，旧 Refresh 立即失效）。

### REQ-4: 登出
系统应支持登出操作，失效用户所有 Refresh Token。

### REQ-5: 业务接口鉴权
除 /api/v1/auth/*、/health、/config/amap 外，所有接口必须在 Authorization Header 携带有效 Access Token，否则返回 code=2001。

#### Scenario: 未登录访问
- GIVEN 没有 Authorization Header
- WHEN 调用 GET /api/v1/routes
- THEN 返回 code=2001

#### Scenario: Token 过期
- GIVEN Access Token 已超过 15 分钟
- WHEN 调用任意业务接口
- THEN 返回 code=2002

### REQ-6: 统一响应格式
所有接口返回格式为 `{"code": 0|错误码, "message": "描述", "data": ...}`，HTTP 状态码恒为 200。
