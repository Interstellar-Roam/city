# 多用户认证体系 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 为 CityWalk 后端增加手机号+验证码登录的双 Token JWT 认证体系，所有业务接口统一鉴权。

**Architecture:** 新增 auth_service 管理验证码和 Token，新增 JWT 中间件拦截所有业务接口，统一 APIResponse 响应格式。

**Tech Stack:** FastAPI, Motor (MongoDB), PyJWT, Pydantic v2, Python 3.12

---

### Task 1: 配置 & 数据模型

**Files:**
- Modify: `app/config.py`
- Modify: `app/models/user.py`
- Create: `app/models/token.py`
- Create: `tests/test_auth_models.py`

**Step 1: Write the failing test**

```python
# tests/test_auth_models.py
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError


class TestUserModel:
    def test_user_requires_phone(self):
        """User 模型 phone 为必填字段"""
        from app.models.user import User
        with pytest.raises(ValidationError):
            User(username="test")  # 缺少 phone 应报错

    def test_user_phone_format(self):
        """phone 必须是字符串"""
        from app.models.user import User
        user = User(phone="13800138000", username="test")
        assert user.phone == "13800138000"

    def test_token_model_fields(self):
        """RefreshToken 模型包含必要字段"""
        from app.models.token import RefreshToken
        token = RefreshToken(
            token="abc123",
            user_id="user1",
            expires_at=datetime.now() + timedelta(days=7)
        )
        assert token.token == "abc123"
        assert token.user_id == "user1"
        assert not token.revoked

    def test_verification_code_model(self):
        """VerificationCode 模型包含 phone, code, expires_at, used"""
        from app.models.token import VerificationCode
        vc = VerificationCode(
            phone="13800138000",
            code="123456",
            expires_at=datetime.now() + timedelta(minutes=5)
        )
        assert vc.phone == "13800138000"
        assert vc.code == "123456"
        assert not vc.used
        assert vc.expires_at > datetime.now()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/rob/CodeBuddy/walk && uv run pytest tests/test_auth_models.py -v`
Expected: FAIL — ValidationError / ModuleNotFoundError

**Step 3: Write minimal implementation**

`app/config.py` 新增:
```python
# JWT 认证配置
jwt_secret: str = Field(default="dev-secret-change-in-production", alias="JWT_SECRET")
jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
sms_mock: bool = Field(default=True, alias="SMS_MOCK")
sms_resend_interval: int = Field(default=60, alias="SMS_RESEND_INTERVAL")
sms_code_expire: int = Field(default=300, alias="SMS_CODE_EXPIRE")
```

`app/models/user.py` 修改（phone 必填，username/email 可选）:
```python
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    phone: str = Field(...)  # 手机号，必填
    username: str | None = None  # 可选
    email: str | None = None
    avatar: str | None = None
    bio: str | None = None
    is_active: bool = True
    total_distance: float = 0.0
    total_routes: int = 0
    total_time: int = 0
    favorite_routes: list[str] = Field(default_factory=list)
    created_routes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

`app/models/token.py`:
```python
from datetime import datetime
from pydantic import BaseModel, Field


class RefreshToken(BaseModel):
    id: str = Field(default_factory=lambda: str(__import__('bson').ObjectId()), alias="_id")
    token: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    revoked: bool = False


class VerificationCode(BaseModel):
    phone: str = Field(..., alias="_id")
    code: str
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    used: bool = False
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/rob/CodeBuddy/walk && uv run pytest tests/test_auth_models.py -v`
Expected: 4 PASS

**Step 5: Commit**

```bash
git add app/config.py app/models/user.py app/models/token.py tests/test_auth_models.py
git commit -m "feat: add auth config, update User model, add Token/VerificationCode models"
```

---

### Task 2: 统一响应格式

**Files:**
- Create: `app/schemas/common.py`
- Modify: `app/api/routes.py`（仅 search 端点做示范适配）
- Create: `tests/test_common_schema.py`

**Step 1: Write the failing test**

```python
# tests/test_common_schema.py
import pytest
from app.schemas.common import APIResponse


class TestAPIResponse:
    def test_success_response(self):
        resp = APIResponse(code=0, message="ok", data={"items": []})
        assert resp.code == 0
        assert resp.message == "ok"
        assert resp.data == {"items": []}

    def test_error_response(self):
        resp = APIResponse(code=2001, message="未登录")
        assert resp.code == 2001
        assert resp.message == "未登录"
        assert resp.data is None

    def test_default_values(self):
        resp = APIResponse()
        assert resp.code == 0
        assert resp.message == "ok"
        assert resp.data is None
```

**Step 2-4: Implement + verify + commit** 略，按 TDD 循环执行。

---

### Task 3: 认证服务 core logic

**Files:**
- Create: `app/services/auth_service.py`
- Modify: `app/database.py`
- Create: `tests/test_auth_service.py`

核心实现：
1. `generate_code(phone)` — Mock: code="123456"，存 MongoDB TTL 索引
2. `verify_code(phone, code)` — 校验验证码，标记 used
3. `create_access_token(user)` — JWT 签发
4. `create_refresh_token(user)` — 随机字符串，存 DB
5. `verify_access_token(token)` — JWT 解码
6. `refresh_tokens(old_refresh_token)` — 轮换

---

### Task 4: 认证路由

**Files:**
- Create: `app/schemas/auth.py`
- Create: `app/api/auth.py`
- Create: `tests/test_auth_api.py`

四个端点：send-code, login, refresh, logout

---

### Task 5: JWT 鉴权中间件

**Files:**
- Create: `app/middleware/auth.py`
- Modify: `app/main.py`
- Create: `tests/test_auth_middleware.py`

---

### Task 6: 现有接口适配

**Files:**
- Modify: `app/api/routes.py`, `search.py`, `sessions.py`, `gps.py`, `navigation.py`

所有 user_id 来源改为 `request.state.user_id`，响应统一 APIResponse。

---

### Task 7: 全量测试 & 归档
- 运行全部测试
- OpenSpec 归档
