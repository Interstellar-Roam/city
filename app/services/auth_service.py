"""认证服务：验证码管理 & JWT Token 签发/验证"""

import hashlib
import secrets
from datetime import datetime, timedelta

import jwt
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.models.token import VerificationCode, RefreshToken


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.settings = get_settings()

    # === 验证码 ===

    async def send_code(self, phone: str) -> tuple[int, str]:
        """发送短信验证码，返回 (code, message)"""
        if not self._is_valid_phone(phone):
            return 1001, "手机号格式不正确"

        # 检查发送频率
        existing = await self.db.verification_codes.find_one({"_id": phone})
        if existing:
            elapsed = (datetime.now() - existing["created_at"]).total_seconds()
            if elapsed < self.settings.sms_resend_interval:
                remaining = int(self.settings.sms_resend_interval - elapsed)
                return 1002, f"请{remaining}秒后重试"

        code = "123456" if self.settings.sms_mock else self._generate_code()
        expires_at = datetime.now() + timedelta(seconds=self.settings.sms_code_expire)

        await self.db.verification_codes.replace_one(
            {"_id": phone},
            VerificationCode(phone=phone, code=code, expires_at=expires_at).model_dump(by_alias=True),
            upsert=True
        )

        logger.info(f"[SMS Mock] 验证码 {code} → {phone}")
        return 0, "ok"

    async def verify_code(self, phone: str, code: str) -> tuple[int, str]:
        """校验验证码，返回 (code, message)"""
        doc = await self.db.verification_codes.find_one({"_id": phone})
        if not doc:
            return 1003, "请先发送验证码"
        if doc["used"]:
            return 1003, "验证码已使用"
        if doc["code"] != code:
            return 1003, "验证码错误"
        if datetime.now() > doc["expires_at"]:
            return 1004, "验证码已过期"

        await self.db.verification_codes.update_one({"_id": phone}, {"$set": {"used": True}})
        return 0, "ok"

    # === Token ===

    async def login(self, phone: str) -> tuple[int, str, dict | None]:
        """登录/注册，返回 (code, message, {access_token, refresh_token, user})"""
        # 查找/创建用户
        user = await self.db.users.find_one({"phone": phone})
        if not user:
            from app.models.user import User
            new_user = User(phone=phone)
            user_doc = new_user.model_dump(by_alias=True)
            await self.db.users.insert_one(user_doc)
            user = user_doc

        user_id = user["_id"]
        access_token = self._create_access_token(user_id, phone)
        refresh_token = await self._create_refresh_token(user_id)

        return 0, "ok", {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.settings.access_token_expire_minutes * 60,
            "user": {"id": user_id, "phone": phone}
        }

    def _create_access_token(self, user_id: str, phone: str) -> str:
        """签发 Access Token (JWT)"""
        payload = {
            "sub": user_id,
            "phone": phone,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=self.settings.access_token_expire_minutes)
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)

    async def _create_refresh_token(self, user_id: str) -> str:
        """创建 Refresh Token（随机字符串，存 MongoDB）"""
        token = secrets.token_urlsafe(64)
        expires_at = datetime.now() + timedelta(days=self.settings.refresh_token_expire_days)

        rt = RefreshToken(token=token, user_id=user_id, expires_at=expires_at)
        await self.db.refresh_tokens.insert_one(rt.model_dump(by_alias=True))
        return token

    @staticmethod
    def verify_access_token(token: str) -> tuple[int, str, dict | None]:
        """验证 Access Token，返回 (code, message, payload)"""
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            return 0, "ok", payload
        except jwt.ExpiredSignatureError:
            return 2002, "Token 已过期", None
        except jwt.InvalidTokenError:
            return 2003, "无效的认证凭证", None

    async def refresh_tokens(self, old_refresh_token: str) -> tuple[int, str, dict | None]:
        """轮换 Token：旧 Refresh 失效，发新 Access + 新 Refresh"""
        doc = await self.db.refresh_tokens.find_one({"token": old_refresh_token, "revoked": False})
        if not doc:
            return 2004, "请重新登录", None
        if datetime.now() > doc["expires_at"]:
            await self.db.refresh_tokens.update_one({"token": old_refresh_token}, {"$set": {"revoked": True}})
            return 2004, "登录已过期，请重新登录", None

        # 失效旧 Token
        await self.db.refresh_tokens.update_one({"token": old_refresh_token}, {"$set": {"revoked": True}})

        # 获取用户信息
        user = await self.db.users.find_one({"_id": doc["user_id"]})
        phone = user["phone"] if user else ""

        # 签发新 Token
        access_token = self._create_access_token(doc["user_id"], phone)
        new_refresh_token = await self._create_refresh_token(doc["user_id"])

        return 0, "ok", {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": self.settings.access_token_expire_minutes * 60
        }

    async def logout(self, user_id: str) -> None:
        """登出：失效所有 Refresh Token"""
        await self.db.refresh_tokens.update_many(
            {"user_id": user_id, "revoked": False},
            {"$set": {"revoked": True}}
        )

    # === 工具方法 ===

    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        return phone.isdigit() and len(phone) == 11 and phone.startswith("1")

    @staticmethod
    def _generate_code() -> str:
        return str(secrets.randbelow(900000) + 100000)
