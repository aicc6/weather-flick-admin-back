"""펫 투어 정보 스키마"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PetTourInfoBase(BaseModel):
    """펫 투어 정보 기본 스키마"""

    pet_tour_id: int
    attraction_content_id: str
    pet_allowed: bool = False
    pet_restrictions: str | None = None
    pet_facilities: str | None = None
    pet_fee: str | None = None
    notes: str | None = None


class PetTourInfoCreate(BaseModel):
    """펫 투어 정보 생성 스키마"""

    attraction_content_id: str
    pet_allowed: bool = False
    pet_restrictions: str | None = None
    pet_facilities: str | None = None
    pet_fee: str | None = None
    notes: str | None = None


class PetTourInfoUpdate(PetTourInfoCreate):
    """펫 투어 정보 수정 스키마"""

    pass


class PetTourInfoResponse(PetTourInfoBase):
    """펫 투어 정보 응답 스키마"""

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PetTourInfoListResponse(BaseModel):
    """펫 투어 정보 목록 응답 스키마"""

    items: list[PetTourInfoResponse]
    total: int


class PetTourInfoSearch(BaseModel):
    """펫 투어 정보 검색 스키마"""

    attraction_content_id: str | None = None
    pet_allowed: bool | None = None
    skip: int = 0
    limit: int = 100