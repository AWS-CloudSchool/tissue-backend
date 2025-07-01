from pydantic import BaseModel, EmailStr, field_validator

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("password_confirm")
    def passwords_match(cls, v, info):
        if info.data and "password" in info.data and v != info.data["password"]:
            raise ValueError("비밀번호가 일치하지 않습니다.")
        return v

class ConfirmSignUpRequest(BaseModel):
    email: EmailStr
    code: str

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str
    email: EmailStr 