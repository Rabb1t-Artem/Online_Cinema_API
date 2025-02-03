from pydantic import BaseModel, ConfigDict


class CustomBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore", underscore_attrs_are_private=True)
