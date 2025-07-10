"""
v3 스키마 데이터베이스 초기화
"""

from sqlalchemy.orm import Session

from app.auth.utils import get_password_hash
from app.database import SessionLocal
from app.models import Admin


def create_v3_tables():
    """v3 데이터베이스 테이블 생성"""
    from app.database import engine
    from app.models import Base

    try:
        # v3 테이블 생성 (이미 존재하면 스킵)
        Base.metadata.create_all(bind=engine)
        print("✅ v3 데이터베이스 테이블 확인/생성 완료")
    except Exception as e:
        print(f"❌ v3 테이블 생성 오류: {e}")


def create_super_admin_v3():
    """v3 스키마에서 슈퍼 관리자 계정 생성"""
    db: Session = SessionLocal()
    try:
        # 기존 슈퍼 관리자 확인
        existing_admin = (
            db.query(Admin).filter(Admin.email == "admin@weatherflick.com").first()
        )

        if existing_admin:
            print("⚠️  v3 슈퍼 관리자 계정이 이미 존재합니다.")
            print(f"   이메일: {existing_admin.email}")
            print(f"   관리자 ID: {existing_admin.admin_id}")
            print(f"   상태: {existing_admin.status}")
            return

        # v3 슈퍼 관리자 계정 생성
        from app.models import AdminStatus

        super_admin = Admin(
            email="admin@weatherflick.com",
            password_hash=get_password_hash("admin123"),
            name="Super Admin",
            status=AdminStatus.ACTIVE,  # v3 enum 사용
        )

        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)

        print("✅ v3 슈퍼 관리자 계정이 생성되었습니다.")
        print(f"   이메일: {super_admin.email}")
        print("   비밀번호: admin123")
        print(f"   관리자 ID: {super_admin.admin_id}")
        print(f"   이름: {super_admin.name}")
        print(f"   상태: {super_admin.status}")

    except Exception as e:
        print(f"❌ v3 슈퍼 관리자 계정 생성 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()


def init_v3_database():
    """v3 데이터베이스 초기화"""
    print("🚀 v3 데이터베이스 초기화를 시작합니다...")

    try:
        create_v3_tables()
        create_super_admin_v3()
        print("✅ v3 데이터베이스 초기화가 완료되었습니다.")

    except Exception as e:
        print(f"❌ v3 데이터베이스 초기화 중 오류 발생: {e}")


if __name__ == "__main__":
    init_v3_database()
