import datetime
from typing import Any, Optional

from fastapi import File, Form, UploadFile
from schemas.custom_base_model import CustomBaseModel


class ProfileRequestForm(CustomBaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    gender: Optional[str]
    date_of_birth: Optional[datetime.date]
    info: Optional[str]
    avatar: Optional[UploadFile]

    @classmethod
    def as_form(
        cls,
        first_name: Optional[str] = Form(),
        last_name: Optional[str] = Form(),
        gender: Optional[str] = Form(),
        date_of_birth: Optional[datetime.date] = Form(),
        info: Optional[str] = Form(),
        avatar: Optional[UploadFile] = File(),
    ) -> Any:
        return cls(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar,
        )


class ProfileResponseSchema(CustomBaseModel):
    id: int
    user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    gender: Optional[str]
    date_of_birth: Optional[datetime.date]
    info: Optional[str]
    avatar: Optional[str]
