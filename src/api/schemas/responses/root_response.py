from pydantic import BaseModel


class RootResponse(BaseModel):
    name: str
    status: str
    docs: str



