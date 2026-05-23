"""认证数据模型测试"""
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError


class TestUserModel:
    def test_user_requires_phone(self):
        """User 模型 phone 为必填字段"""
        from app.models.user import User
        with pytest.raises(ValidationError):
            User(username="test")

    def test_user_phone_accepted(self):
        """phone 字段应正常接受"""
        from app.models.user import User
        user = User(phone="13800138000")
        assert user.phone == "13800138000"

    def test_user_is_active_default(self):
        """is_active 默认 True"""
        from app.models.user import User
        user = User(phone="13800138000")
        assert user.is_active is True


class TestTokenModels:
    def test_refresh_token_fields(self):
        """RefreshToken 包含 token, user_id, expires_at, revoked"""
        from app.models.token import RefreshToken
        token = RefreshToken(
            token="abc123def456",
            user_id="user_001",
            expires_at=datetime.now() + timedelta(days=7)
        )
        assert token.token == "abc123def456"
        assert token.user_id == "user_001"
        assert not token.revoked
        assert token.expires_at > datetime.now()

    def test_verification_code_fields(self):
        """VerificationCode 包含 phone, code, expires_at, used"""
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
