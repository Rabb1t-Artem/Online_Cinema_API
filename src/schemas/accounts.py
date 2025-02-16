from pydantic import EmailStr, field_validator
from schemas.custom_base_model import CustomBaseModel

from database import accounts_validators


class BaseEmailPasswordSchema(CustomBaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return accounts_validators.validate_password_strength(value)


class ChangePasswordRequestSchema(CustomBaseModel):
    email: str
    old_password: str
    new_password: str


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class PasswordResetRequestSchema(CustomBaseModel):
    email: EmailStr


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    token: str


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    pass


class UserLoginResponseSchema(CustomBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegistrationResponseSchema(CustomBaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}


class UserActivationRequestSchema(CustomBaseModel):
    email: EmailStr
    token: str


class MessageResponseSchema(CustomBaseModel):
    message: str


class TokenRefreshRequestSchema(CustomBaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(CustomBaseModel):
    access_token: str
    token_type: str = "bearer"
