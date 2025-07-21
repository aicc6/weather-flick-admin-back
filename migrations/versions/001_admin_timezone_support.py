"""Add timezone support to admin backend tables

Revision ID: 001_admin_timezone
Revises: 
Create Date: 2025-01-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_admin_timezone'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    관리자 백엔드 테이블들에 타임존 지원 추가
    admins, admin_batch_jobs, admin_batch_job_details 등
    """
    
    print("관리자 백엔드 테이블 마이그레이션 시작...")
    
    # =============================================================================
    # 관리자 테이블
    # =============================================================================
    
    # admins 테이블 (이미 일부는 timezone-aware일 수 있음)
    print("  - admins 테이블 마이그레이션...")
    
    # created_at이 timezone-aware가 아닌 경우만 변경
    try:
        op.execute("""
            ALTER TABLE admins 
            ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
            USING created_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
        """)
    except Exception as e:
        print(f"    Info: admins.created_at 이미 timezone-aware이거나 필드가 없음: {e}")
    
    # updated_at 처리
    try:
        op.execute("""
            ALTER TABLE admins 
            ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE 
            USING updated_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
        """)
    except Exception as e:
        print(f"    Info: admins.updated_at 이미 timezone-aware이거나 필드가 없음: {e}")
    
    # last_login_at은 이미 UTC로 저장되고 있음 (datetime.now(UTC) 사용)
    try:
        op.execute("""
            ALTER TABLE admins 
            ALTER COLUMN last_login_at TYPE TIMESTAMP WITH TIME ZONE 
            USING last_login_at AT TIME ZONE 'UTC'
        """)
    except Exception as e:
        print(f"    Info: admins.last_login_at 이미 timezone-aware이거나 필드가 없음: {e}")
    
    # =============================================================================
    # 배치 작업 테이블들 (이미 timezone-aware일 가능성 높음)
    # =============================================================================
    
    batch_tables = [
        ('admin_batch_jobs', ['created_at', 'updated_at', 'started_at', 'finished_at']),
        ('admin_batch_job_details', ['created_at', 'timestamp'])
    ]
    
    for table_name, columns in batch_tables:
        print(f"  - {table_name} 테이블 확인...")
        
        for column in columns:
            try:
                # 이미 timezone-aware인지 확인
                result = op.get_bind().execute(f"""
                    SELECT data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    AND column_name = '{column}'
                """).fetchone()
                
                if result and 'timestamp without time zone' in str(result[0]).lower():
                    print(f"    - {column} 필드를 timezone-aware로 변경...")
                    op.execute(f"""
                        ALTER TABLE {table_name} 
                        ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE 
                        USING {column} AT TIME ZONE 'UTC'
                    """)
                else:
                    print(f"    - {column} 필드는 이미 timezone-aware이거나 다른 타입입니다.")
                    
            except Exception as e:
                print(f"    Warning: {table_name}.{column} 처리 중 오류: {e}")
    
    # =============================================================================
    # 연락처 관련 테이블들 (이미 timezone-aware일 가능성 높음)
    # =============================================================================
    
    contact_tables = ['contact_messages', 'contact_responses']
    
    for table_name in contact_tables:
        print(f"  - {table_name} 테이블 확인...")
        
        try:
            # 이미 timezone-aware인지 확인
            result = op.get_bind().execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND column_name IN ('created_at', 'updated_at')
                AND data_type = 'timestamp without time zone'
            """).fetchall()
            
            for row in result:
                column = row[0]
                print(f"    - {column} 필드를 timezone-aware로 변경...")
                op.execute(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE 
                    USING {column} AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
                """)
                
        except Exception as e:
            print(f"    Info: {table_name} 테이블은 이미 적절히 설정되었거나 존재하지 않음: {e}")
    
    print("관리자 백엔드 테이블 마이그레이션 완료")


def downgrade() -> None:
    """
    롤백: 관리자 테이블들의 timezone-aware 필드를 다시 naive datetime으로 변경
    """
    
    print("관리자 백엔드 테이블 롤백 시작...")
    
    # admins 테이블 롤백
    try:
        op.execute("""
            ALTER TABLE admins 
            ALTER COLUMN created_at TYPE TIMESTAMP 
            USING created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
        """)
        
        op.execute("""
            ALTER TABLE admins 
            ALTER COLUMN updated_at TYPE TIMESTAMP 
            USING updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
        """)
        
        op.execute("""
            ALTER TABLE admins 
            ALTER COLUMN last_login_at TYPE TIMESTAMP 
            USING last_login_at AT TIME ZONE 'UTC'
        """)
    except Exception as e:
        print(f"    Warning: admins 테이블 롤백 중 오류: {e}")
    
    # 배치 테이블들 롤백
    batch_tables = ['admin_batch_jobs', 'admin_batch_job_details']
    
    for table_name in batch_tables:
        try:
            # 테이블의 모든 timestamp with time zone 컬럼을 찾아서 롤백
            result = op.get_bind().execute(f"""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND data_type = 'timestamp with time zone'
            """).fetchall()
            
            for row in result:
                column = row[0]
                op.execute(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN {column} TYPE TIMESTAMP 
                    USING {column} AT TIME ZONE 'UTC'
                """)
                
        except Exception as e:
            print(f"    Warning: {table_name} 테이블 롤백 중 오류: {e}")
    
    # 연락처 테이블들 롤백
    contact_tables = ['contact_messages', 'contact_responses']
    
    for table_name in contact_tables:
        try:
            op.execute(f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN created_at TYPE TIMESTAMP 
                USING created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
            """)
            
            op.execute(f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN updated_at TYPE TIMESTAMP 
                USING updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
            """)
        except Exception as e:
            print(f"    Warning: {table_name} 테이블 롤백 중 오류: {e}")
    
    print("관리자 백엔드 테이블 롤백 완료")