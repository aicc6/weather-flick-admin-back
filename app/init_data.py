from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Admin
from app.auth.utils import get_password_hash


def create_tables():
    """데이터베이스 테이블 생성"""
    # 기존 테이블이 있으므로 테이블 생성은 스킵
    print("ℹ️  기존 데이터베이스 테이블을 사용합니다.")


def create_super_admin():
    """슈퍼 관리자 계정 생성"""
    db: Session = SessionLocal()
    try:
        # 기존 슈퍼 관리자 확인
        existing_admin = (
            db.query(Admin).filter(Admin.email == "admin@weatherflick.com").first()
        )

        if existing_admin:
            print("⚠️  슈퍼 관리자 계정이 이미 존재합니다.")
            print(f"   이메일: {existing_admin.email}")
            print(f"   관리자 ID: {existing_admin.id}")
            print(f"   상태: {existing_admin.status}")
            return

        # 슈퍼 관리자 계정 생성
        super_admin = Admin(
            email="admin@weatherflick.com",
            password_hash=get_password_hash("admin123"),
            name="Super Admin",
            status="ACTIVE",
        )

        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)

        print("✅ 슈퍼 관리자 계정이 생성되었습니다.")
        print(f"   이메일: {super_admin.email}")
        print(f"   비밀번호: admin123")
        print(f"   관리자 ID: {super_admin.id}")
        print(f"   이름: {super_admin.name}")
        print(f"   상태: {super_admin.status}")

    except Exception as e:
        print(f"❌ 슈퍼 관리자 계정 생성 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()


def init_database():
    """데이터베이스 초기화"""
    print("🚀 데이터베이스 초기화를 시작합니다...")

    try:
        create_tables()
        create_super_admin()
        print("✅ 데이터베이스 초기화가 완료되었습니다.")

    except Exception as e:
        print(f"❌ 데이터베이스 초기화 중 오류 발생: {e}")


if __name__ == "__main__":
    init_database()
