import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.rbac_dependencies import require_permission, require_super_admin
from ..auth.utils import generate_temporary_password, get_password_hash
from ..database import get_db
from ..models_admin import Admin, AdminStatus
from ..models_admin import Admin as CurrentAdmin
from ..schemas.admin_schemas import (
    AdminCreate,
    AdminListResponse,
    AdminResponse,
    AdminStatusUpdate,
    AdminUpdate,
)

router = APIRouter(prefix="/admins", tags=["Admin Management"])


@router.post("/", response_model=AdminResponse)
async def create_admin(
    admin_create: AdminCreate,
    current_admin: CurrentAdmin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """새 관리자 계정 생성 (슈퍼관리자만 가능)"""
    # 이메일 중복 확인
    existing_admin = db.query(Admin).filter(Admin.email == admin_create.email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다",
        )

    # 비밀번호 해싱
    hashed_password = get_password_hash(admin_create.password)

    # 새 관리자 생성
    new_admin = Admin(
        email=admin_create.email,
        password_hash=hashed_password,
        name=admin_create.name,
        phone=admin_create.phone,
        is_superuser=admin_create.is_superuser,
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    # 역할 할당 (슈퍼유저가 아닌 경우)
    if not admin_create.is_superuser and admin_create.role_ids:
        from ..models_rbac import Role

        for role_id in admin_create.role_ids:
            role = db.query(Role).filter(Role.id == role_id).first()
            if role:
                new_admin.roles.append(role)
        db.commit()
        db.refresh(new_admin)

    # 관리자의 역할 ID 목록 가져오기
    role_ids = [role.id for role in new_admin.roles] if hasattr(new_admin, 'roles') else []
    
    admin_dict = {
        "admin_id": new_admin.admin_id,
        "email": new_admin.email,
        "name": new_admin.name,
        "phone": new_admin.phone,
        "status": new_admin.status.value if hasattr(new_admin.status, 'value') else new_admin.status,
        "is_superuser": new_admin.is_superuser,
        "last_login_at": new_admin.last_login_at,
        "created_at": new_admin.created_at,
        "role_ids": role_ids,
    }
    return AdminResponse.model_validate(admin_dict)


@router.get("/roles")
async def get_available_roles(
    current_admin: CurrentAdmin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """사용 가능한 역할 목록 조회 (슈퍼관리자만 가능)"""
    from ..models_rbac import Role

    roles = db.query(Role).all()

    return {
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "display_name": role.display_name,
                "description": role.description,
                "is_system": role.is_system,
            }
            for role in roles
        ]
    }


@router.get("/", response_model=AdminListResponse)
async def get_admin_list(
    current_admin: CurrentAdmin = Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    status: str | None = Query(
        None, description="상태 필터 (ACTIVE, INACTIVE, LOCKED)"
    ),
    search: str | None = Query(None, description="이메일 또는 이름으로 검색"),
):
    """관리자 목록 조회 (슈퍼관리자만 가능)"""

    # 기본 쿼리
    query = db.query(Admin)

    # 상태 필터
    if status:
        query = query.filter(Admin.status == status)

    # 검색 필터
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Admin.email.ilike(search_filter)) | (Admin.name.ilike(search_filter))
        )

    # 전체 개수 조회
    total = query.count()

    # 페이지네이션 적용
    offset = (page - 1) * size
    admins = query.order_by(Admin.created_at.desc()).offset(offset).limit(size).all()

    admin_responses = []
    for admin in admins:
        # 관리자의 역할 ID 목록 가져오기
        role_ids = [role.id for role in admin.roles] if hasattr(admin, 'roles') else []
        
        admin_dict = {
            "admin_id": admin.admin_id,
            "email": admin.email,
            "name": admin.name,
            "phone": admin.phone,
            "status": admin.status.value if hasattr(admin.status, 'value') else admin.status,
            "is_superuser": admin.is_superuser,
            "last_login_at": admin.last_login_at,
            "created_at": admin.created_at,
            "role_ids": role_ids,
        }
        admin_responses.append(AdminResponse.model_validate(admin_dict))

    # 총 페이지 수 계산
    total_pages = math.ceil(total / size)

    return AdminListResponse(
        admins=admin_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get("/stats")
async def get_admin_statistics(
    current_admin: CurrentAdmin = Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
):
    """관리자 통계 조회 (슈퍼관리자만 가능)"""
    try:
        total = db.query(Admin).count()
        active = db.query(Admin).filter(Admin.status == AdminStatus.ACTIVE).count()
        inactive = db.query(Admin).filter(Admin.status == AdminStatus.INACTIVE).count()

        return {"total": total, "active": active, "inactive": inactive}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="관리자 통계 조회 중 오류가 발생했습니다",
        )


@router.get("/{admin_id}", response_model=AdminResponse)
async def get_admin_detail(
    admin_id: int,
    current_admin: CurrentAdmin = Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
):
    """특정 관리자 상세 조회 (슈퍼관리자만 가능)"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 관리자의 역할 ID 목록 가져오기
    role_ids = [role.id for role in admin.roles] if hasattr(admin, 'roles') else []
    
    admin_dict = {
        "admin_id": admin.admin_id,
        "email": admin.email,
        "name": admin.name,
        "phone": admin.phone,
        "status": admin.status.value if hasattr(admin.status, 'value') else admin.status,
        "is_superuser": admin.is_superuser,
        "last_login_at": admin.last_login_at,
        "created_at": admin.created_at,
        "role_ids": role_ids,
    }
    return AdminResponse.model_validate(admin_dict)


@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    admin_update: AdminUpdate,
    current_admin: CurrentAdmin = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """관리자 정보 수정 (슈퍼관리자만 가능)"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 업데이트할 필드들 적용
    if admin_update.email is not None:
        # 이메일 중복 확인
        existing_admin = db.query(Admin).filter(
            Admin.email == admin_update.email,
            Admin.admin_id != admin_id
        ).first()
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 이메일입니다"
            )
        admin.email = admin_update.email
    
    if admin_update.name is not None:
        admin.name = admin_update.name
    
    if admin_update.phone is not None:
        admin.phone = admin_update.phone
    
    if admin_update.password is not None and admin_update.password:
        # 비밀번호 해싱
        admin.password_hash = get_password_hash(admin_update.password)
    
    if admin_update.status is not None:
        # 자기 자신의 상태는 변경할 수 없음
        if (
            admin.admin_id == current_admin.admin_id
            and admin_update.status != admin.status
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자신의 계정 상태는 변경할 수 없습니다",
            )
        # 슈퍼관리자의 상태는 변경할 수 없음
        if admin.is_superuser and admin_update.status != admin.status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="슈퍼관리자의 상태는 변경할 수 없습니다.",
            )
        admin.status = admin_update.status

    db.commit()
    db.refresh(admin)

    # 관리자의 역할 ID 목록 가져오기
    role_ids = [role.id for role in admin.roles] if hasattr(admin, 'roles') else []
    
    admin_dict = {
        "admin_id": admin.admin_id,
        "email": admin.email,
        "name": admin.name,
        "phone": admin.phone,
        "status": admin.status.value if hasattr(admin.status, 'value') else admin.status,
        "is_superuser": admin.is_superuser,
        "last_login_at": admin.last_login_at,
        "created_at": admin.created_at,
        "role_ids": role_ids,
    }
    return AdminResponse.model_validate(admin_dict)


@router.put("/{admin_id}/status", response_model=AdminResponse)
async def update_admin_status(
    admin_id: int,
    status_update: AdminStatusUpdate,
    current_admin: CurrentAdmin = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """관리자 상태 변경 (슈퍼관리자만 가능)"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신의 상태는 변경할 수 없음
    if admin.admin_id == current_admin.admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정 상태는 변경할 수 없습니다",
        )

    # 슈퍼관리자는 상태 변경할 수 없음
    if admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="슈퍼관리자는 비활성화할 수 없습니다.",
        )

    # 상태 값 검증
    valid_statuses = ["ACTIVE", "INACTIVE", "LOCKED"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 상태입니다. 가능한 값: {valid_statuses}",
        )

    admin.status = status_update.status
    db.commit()
    db.refresh(admin)

    # 관리자의 역할 ID 목록 가져오기
    role_ids = [role.id for role in admin.roles] if hasattr(admin, 'roles') else []
    
    admin_dict = {
        "admin_id": admin.admin_id,
        "email": admin.email,
        "name": admin.name,
        "phone": admin.phone,
        "status": admin.status.value if hasattr(admin.status, 'value') else admin.status,
        "is_superuser": admin.is_superuser,
        "last_login_at": admin.last_login_at,
        "created_at": admin.created_at,
        "role_ids": role_ids,
    }
    return AdminResponse.model_validate(admin_dict)


@router.delete("/{admin_id}")
async def deactivate_admin(
    admin_id: int,
    current_admin: CurrentAdmin = Depends(require_permission("roles.delete")),
    db: Session = Depends(get_db),
):
    """관리자 계정 비활성화 (슈퍼관리자만 가능)"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신은 비활성화할 수 없음
    if admin.admin_id == current_admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정은 비활성화할 수 없습니다",
        )

    # 슈퍼관리자는 비활성화할 수 없음
    if admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="슈퍼관리자는 비활성화할 수 없습니다.",
        )

    # 이미 비활성화된 계정인지 확인
    if admin.status == AdminStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미 비활성화된 계정입니다"
        )

    admin.status = AdminStatus.INACTIVE
    db.commit()

    return {"message": f"관리자 '{admin.name}' 계정이 비활성화되었습니다"}


@router.delete("/{admin_id}/permanent")
async def delete_admin_permanently(
    admin_id: int,
    current_admin: CurrentAdmin = Depends(require_permission("roles.delete")),
    db: Session = Depends(get_db),
):
    """관리자 계정 완전 삭제 (슈퍼관리자만 가능)"""

    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신은 삭제할 수 없음
    if admin.admin_id == current_admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정은 삭제할 수 없습니다",
        )

    # 슈퍼관리자는 삭제할 수 없음
    if admin.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="슈퍼관리자는 삭제할 수 없습니다.",
        )

    admin_name = admin.name or admin.email
    db.delete(admin)
    db.commit()

    return {"message": f"관리자 '{admin_name}' 계정이 완전히 삭제되었습니다"}


@router.post("/{admin_id}/reset-password")
async def reset_admin_password(
    admin_id: int,
    current_admin: CurrentAdmin = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """관리자 비밀번호 초기화 (슈퍼관리자만 가능)"""
    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 보안 강화된 임시 비밀번호 생성
    temp_password = generate_temporary_password()
    admin.password_hash = get_password_hash(temp_password)

    db.commit()

    return {
        "message": f"관리자 '{admin.name or admin.email}' 비밀번호가 초기화되었습니다",
        "admin_id": admin_id,
        "temporary_password": temp_password,
    }


@router.put("/{admin_id}/roles")
async def update_admin_roles(
    admin_id: int,
    role_data: dict,
    current_admin: CurrentAdmin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """관리자 역할 수정 (슈퍼관리자만 가능)"""
    from ..models_rbac import Role

    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다"
        )

    # 자기 자신의 권한은 변경할 수 없음
    if admin.admin_id == current_admin.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 권한은 변경할 수 없습니다",
        )

    # 슈퍼유저 권한 업데이트
    if "is_superuser" in role_data:
        admin.is_superuser = role_data["is_superuser"]

    # 기존 역할 제거
    admin.roles.clear()

    # 슈퍼유저가 아닌 경우 새 역할 할당
    if not admin.is_superuser and "role_ids" in role_data:
        for role_id in role_data["role_ids"]:
            role = db.query(Role).filter(Role.id == role_id).first()
            if role:
                admin.roles.append(role)

    db.commit()
    db.refresh(admin)

    return {
        "message": f"관리자 '{admin.name or admin.email}' 권한이 업데이트되었습니다"
    }


@router.get("/permissions/matrix")
async def get_permissions_matrix(
    current_admin: CurrentAdmin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """권한 매트릭스 조회 (슈퍼관리자만 가능)"""
    from ..models_rbac import Permission, Role

    roles = db.query(Role).all()
    permissions = db.query(Permission).all()

    matrix = []
    for role in roles:
        role_permissions = [perm.name for perm in role.permissions]
        matrix.append(
            {
                "role_id": role.id,
                "role_name": role.name,
                "display_name": role.display_name,
                "description": role.description,
                "is_system": role.is_system,
                "permissions": role_permissions,
            }
        )

    return {
        "roles": matrix,
        "all_permissions": [
            {"id": p.id, "name": p.name, "description": p.description}
            for p in permissions
        ],
    }


@router.post("/roles")
async def create_role(
    role_data: dict,
    current_admin: CurrentAdmin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """새 역할 생성 (슈퍼관리자만 가능)"""
    from ..models_rbac import Permission, Role

    # 기본 역할 정보 생성
    new_role = Role(
        name=role_data.get("name"),
        display_name=role_data.get("display_name"),
        description=role_data.get("description"),
        is_system=False,  # 사용자 생성 역할은 시스템 역할이 아님
    )

    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    # 권한 할당
    if "permission_ids" in role_data:
        for permission_id in role_data["permission_ids"]:
            permission = (
                db.query(Permission).filter(Permission.id == permission_id).first()
            )
            if permission:
                new_role.permissions.append(permission)
        db.commit()
        db.refresh(new_role)

    return {
        "message": f"역할 '{new_role.display_name}'이 생성되었습니다",
        "role_id": new_role.id,
    }


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    role_data: dict,
    current_admin: CurrentAdmin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """역할 정보 및 권한 수정 (슈퍼관리자만 가능)"""
    from ..models_rbac import Permission, Role

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="역할을 찾을 수 없습니다"
        )

    # 시스템 역할은 수정 불가
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="시스템 역할은 수정할 수 없습니다",
        )

    # 역할 정보 업데이트
    if "display_name" in role_data:
        role.display_name = role_data["display_name"]
    if "description" in role_data:
        role.description = role_data["description"]

    # 권한 업데이트
    if "permission_ids" in role_data:
        role.permissions.clear()
        for permission_id in role_data["permission_ids"]:
            permission = (
                db.query(Permission).filter(Permission.id == permission_id).first()
            )
            if permission:
                role.permissions.append(permission)

    db.commit()
    db.refresh(role)

    return {"message": f"역할 '{role.display_name}'이 수정되었습니다"}


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_admin: CurrentAdmin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """역할 삭제 (슈퍼관리자만 가능)"""
    from ..models_rbac import Role

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="역할을 찾을 수 없습니다"
        )

    # 시스템 역할은 삭제 불가
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="시스템 역할은 삭제할 수 없습니다",
        )

    # 해당 역할을 가진 관리자가 있는지 확인
    if role.admins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="해당 역할을 사용 중인 관리자가 있어 삭제할 수 없습니다",
        )

    role_name = role.display_name
    db.delete(role)
    db.commit()

    return {"message": f"역할 '{role_name}'이 삭제되었습니다"}


@router.get("/permissions")
async def get_all_permissions(
    current_admin: CurrentAdmin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """모든 권한 목록 조회 (슈퍼관리자만 가능)"""
    from ..models_rbac import Permission

    permissions = db.query(Permission).all()

    return {
        "permissions": [
            {
                "id": permission.id,
                "name": permission.name,
                "description": permission.description,
            }
            for permission in permissions
        ]
    }
