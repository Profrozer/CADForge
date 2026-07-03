from pydantic import BaseModel, Field


class GenerationSettings(BaseModel):
    max_retries: int = Field(default=2, ge=0, le=5)
    units: str = "mm"
    timeout_seconds: int = Field(default=90, ge=10, le=300)


class GenerateRequest(BaseModel):
    prompt: str
    provider: str
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    # When iterating on an existing part, the client sends the part id and the
    # version whose code should be edited.
    part_id: str | None = None
    base_version: int | None = None
    settings: GenerationSettings = GenerationSettings()


class TestKeyRequest(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class ModelsRequest(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None


class ThumbnailRequest(BaseModel):
    part_id: str
    version: int
    data_url: str
