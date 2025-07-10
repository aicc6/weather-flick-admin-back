"""
데이터 품질 점수 시스템

여행지 데이터의 완성도와 정확성을 평가하여 점수를 산정하는 서비스
"""

import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class DataQualityAnalyzer:
    """데이터 품질 분석기"""

    def __init__(self, db: Session):
        self.db = db

        # 품질 평가 가중치 설정
        self.weights = {
            "completeness": 0.35,  # 완성도 (35%)
            "accuracy": 0.25,  # 정확성 (25%)
            "consistency": 0.20,  # 일관성 (20%)
            "validity": 0.15,  # 유효성 (15%)
            "freshness": 0.05,  # 최신성 (5%)
        }

        # 필수 필드 정의
        self.required_fields = {
            "destinations": ["name", "province", "latitude", "longitude"],
            "restaurants": ["restaurant_name", "region_code"],
            "accommodations": ["name", "province", "latitude", "longitude"],  # destinations 숙박 데이터 사용
        }

        # 선택 필드 정의 (품질 향상에 기여)
        self.optional_fields = {
            "destinations": ["region", "category", "image_url", "amenities", "rating"],
            "restaurants": ["cuisine_type", "operating_hours", "tel", "homepage"],
            "accommodations": ["region", "image_url", "amenities", "rating"],  # destinations 숙박 데이터 필드
        }

    def calculate_destination_quality_score(
        self, destination_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        여행지 데이터의 품질 점수를 계산

        Args:
            destination_data: 여행지 데이터 딕셔너리

        Returns:
            Dict containing quality scores and details
        """
        scores = {}
        details = {}

        # 1. 완성도 점수 (Completeness)
        completeness_score, completeness_details = self._calculate_completeness_score(
            destination_data, "destinations"
        )
        scores["completeness"] = completeness_score
        details["completeness"] = completeness_details

        # 2. 정확성 점수 (Accuracy)
        accuracy_score, accuracy_details = self._calculate_accuracy_score(
            destination_data
        )
        scores["accuracy"] = accuracy_score
        details["accuracy"] = accuracy_details

        # 3. 일관성 점수 (Consistency)
        consistency_score, consistency_details = self._calculate_consistency_score(
            destination_data
        )
        scores["consistency"] = consistency_score
        details["consistency"] = consistency_details

        # 4. 유효성 점수 (Validity)
        validity_score, validity_details = self._calculate_validity_score(
            destination_data
        )
        scores["validity"] = validity_score
        details["validity"] = validity_details

        # 5. 최신성 점수 (Freshness)
        freshness_score, freshness_details = self._calculate_freshness_score(
            destination_data
        )
        scores["freshness"] = freshness_score
        details["freshness"] = freshness_details

        # 최종 품질 점수 계산 (가중 평균)
        total_score = sum(
            scores[category] * self.weights[category] for category in scores.keys()
        )

        return {
            "total_score": round(total_score, 2),
            "category_scores": scores,
            "details": details,
            "grade": self._get_quality_grade(total_score),
            "recommendations": self._generate_quality_recommendations(scores, details),
        }

    def _calculate_completeness_score(
        self, data: dict[str, Any], table_name: str
    ) -> tuple[float, dict[str, Any]]:
        """완성도 점수 계산"""
        required = self.required_fields.get(table_name, [])
        optional = self.optional_fields.get(table_name, [])

        # 필수 필드 완성도 (70% 가중치)
        required_filled = sum(
            1 for field in required if self._is_field_filled(data.get(field))
        )
        required_score = (required_filled / len(required)) * 100 if required else 100

        # 선택 필드 완성도 (30% 가중치)
        optional_filled = sum(
            1 for field in optional if self._is_field_filled(data.get(field))
        )
        optional_score = (optional_filled / len(optional)) * 100 if optional else 100

        # 가중 평균 계산
        total_score = (required_score * 0.7) + (optional_score * 0.3)

        details = {
            "required_fields": {
                "total": len(required),
                "filled": required_filled,
                "score": round(required_score, 2),
            },
            "optional_fields": {
                "total": len(optional),
                "filled": optional_filled,
                "score": round(optional_score, 2),
            },
            "missing_required": [
                field
                for field in required
                if not self._is_field_filled(data.get(field))
            ],
            "missing_optional": [
                field
                for field in optional
                if not self._is_field_filled(data.get(field))
            ],
        }

        return round(total_score, 2), details

    def _calculate_accuracy_score(
        self, data: dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        """정확성 점수 계산"""
        accuracy_score = 100.0
        issues = []

        # 좌표 정확성 검사
        lat = data.get("latitude")
        lng = data.get("longitude")

        if lat is not None and lng is not None:
            try:
                lat_float = float(lat)
                lng_float = float(lng)

                # 한국 영토 내 좌표인지 확인 (대략적인 범위)
                if not (33.0 <= lat_float <= 38.9 and 124.0 <= lng_float <= 132.0):
                    accuracy_score -= 15
                    issues.append("좌표가 한국 영토 범위를 벗어남")

            except (ValueError, TypeError):
                accuracy_score -= 20
                issues.append("잘못된 좌표 형식")

        # 전화번호 형식 검사
        tel = data.get("tel") or data.get("phone")
        if tel and not self._is_valid_phone_number(str(tel)):
            accuracy_score -= 10
            issues.append("잘못된 전화번호 형식")

        # 이메일 형식 검사 (homepage에서 추출 가능한 경우)
        homepage = data.get("homepage")
        if homepage and "@" in homepage and not self._is_valid_email_in_text(homepage):
            accuracy_score -= 5
            issues.append("홈페이지에 잘못된 이메일 형식 포함")

        # 주소 정확성 (기본적인 한국 주소 패턴)
        address = data.get("address")
        if address and not self._is_valid_korean_address(str(address)):
            accuracy_score -= 10
            issues.append("주소 형식이 한국 주소 패턴과 맞지 않음")

        # 평점 범위 검사
        rating = data.get("rating")
        if rating is not None:
            try:
                rating_float = float(rating)
                if not (0.0 <= rating_float <= 5.0):
                    accuracy_score -= 5
                    issues.append("평점이 유효 범위(0-5)를 벗어남")
            except (ValueError, TypeError):
                accuracy_score -= 5
                issues.append("잘못된 평점 형식")

        details = {
            "issues": issues,
            "checks_performed": [
                "coordinate_bounds",
                "phone_format",
                "email_format",
                "address_pattern",
                "rating_range",
            ],
        }

        return max(0, round(accuracy_score, 2)), details

    def _calculate_consistency_score(
        self, data: dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        """일관성 점수 계산"""
        consistency_score = 100.0
        issues = []

        # 이름과 주소의 지역 일관성 검사
        name = (
            data.get("name")
            or data.get("attraction_name")
            or data.get("restaurant_name")
        )
        address = data.get("address")
        province = data.get("province")

        if name and address and province:
            # 주소에 도/시 정보가 포함되어 있는지 확인
            if province not in address:
                consistency_score -= 10
                issues.append("주소와 도/시 정보가 일치하지 않음")

        # 카테고리와 이름의 일관성
        category = data.get("category") or data.get("category_name")
        if name and category:
            # 기본적인 카테고리-이름 일관성 검사
            if "박물관" in category and "박물관" not in name and "미술관" not in name:
                consistency_score -= 5
                issues.append("카테고리와 이름이 일치하지 않을 수 있음")

        # 좌표와 주소의 일관성 (시/도 레벨에서)
        lat = data.get("latitude")
        lng = data.get("longitude")
        if lat and lng and province:
            expected_province = self._get_province_from_coordinates(
                float(lat), float(lng)
            )
            if expected_province and expected_province != province:
                consistency_score -= 15
                issues.append(
                    f"좌표 위치({expected_province})와 도/시 정보({province})가 불일치"
                )

        details = {
            "issues": issues,
            "checks_performed": [
                "address_province_consistency",
                "category_name_consistency",
                "coordinate_address_consistency",
            ],
        }

        return max(0, round(consistency_score, 2)), details

    def _calculate_validity_score(
        self, data: dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        """유효성 점수 계산"""
        validity_score = 100.0
        issues = []

        # URL 유효성 검사
        homepage = data.get("homepage")
        if homepage:
            if not self._is_valid_url(str(homepage)):
                validity_score -= 15
                issues.append("잘못된 홈페이지 URL 형식")

        # 이미지 URL 유효성
        image_fields = ["image_url", "first_image", "first_image_small"]
        for field in image_fields:
            image_url = data.get(field)
            if image_url and not self._is_valid_image_url(str(image_url)):
                validity_score -= 10
                issues.append(f"잘못된 이미지 URL 형식: {field}")

        # JSON 필드 유효성
        json_fields = ["amenities", "detail_intro_info", "detail_additional_info"]
        for field in json_fields:
            json_data = data.get(field)
            if json_data and not self._is_valid_json(json_data):
                validity_score -= 5
                issues.append(f"잘못된 JSON 형식: {field}")

        # 날짜 형식 유효성
        date_fields = ["created_at", "updated_at", "last_sync_at"]
        for field in date_fields:
            date_value = data.get(field)
            if date_value and not self._is_valid_date(date_value):
                validity_score -= 5
                issues.append(f"잘못된 날짜 형식: {field}")

        details = {
            "issues": issues,
            "checks_performed": [
                "url_validity",
                "image_url_validity",
                "json_validity",
                "date_validity",
            ],
        }

        return max(0, round(validity_score, 2)), details

    def _calculate_freshness_score(
        self, data: dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        """최신성 점수 계산"""
        freshness_score = 100.0

        # 마지막 업데이트 날짜 확인
        updated_at = data.get("updated_at") or data.get("last_sync_at")

        if updated_at:
            try:
                if isinstance(updated_at, str):
                    update_date = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                else:
                    update_date = updated_at

                # 현재 시점에서 얼마나 오래되었는지 계산
                days_old = (datetime.now() - update_date.replace(tzinfo=None)).days

                # 30일 이내: 100점, 90일 이내: 80점, 180일 이내: 60점, 그 이상: 40점
                if days_old <= 30:
                    freshness_score = 100
                elif days_old <= 90:
                    freshness_score = 80
                elif days_old <= 180:
                    freshness_score = 60
                else:
                    freshness_score = 40

            except Exception:
                freshness_score = 50  # 날짜 파싱 실패 시 중간 점수
        else:
            freshness_score = 30  # 업데이트 날짜 정보 없음

        details = {
            "last_updated": str(updated_at) if updated_at else None,
            "days_since_update": None,
            "status": (
                "fresh"
                if freshness_score >= 80
                else "moderate" if freshness_score >= 60 else "stale"
            ),
        }

        return round(freshness_score, 2), details

    def _is_field_filled(self, value: Any) -> bool:
        """필드가 채워져 있는지 확인"""
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True

    def _is_valid_phone_number(self, phone: str) -> bool:
        """한국 전화번호 패턴 검증"""
        patterns = [
            r"^0\d{1,2}-\d{3,4}-\d{4}$",  # 02-1234-5678
            r"^0\d{9,10}$",  # 01012345678
            r"^\d{3}-\d{3,4}-\d{4}$",  # 010-1234-5678
        ]
        return any(re.match(pattern, phone.replace(" ", "")) for pattern in patterns)

    def _is_valid_email_in_text(self, text: str) -> bool:
        """텍스트 내 이메일 형식 검증"""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, text)
        return len(emails) > 0

    def _is_valid_korean_address(self, address: str) -> bool:
        """한국 주소 패턴 검증"""
        korean_regions = [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주",
            "대전",
            "울산",
            "세종",
            "경기",
            "강원",
            "충북",
            "충남",
            "전북",
            "전남",
            "경북",
            "경남",
            "제주",
        ]
        return any(region in address for region in korean_regions)

    def _is_valid_url(self, url: str) -> bool:
        """URL 형식 검증"""
        url_pattern = r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
        return re.match(url_pattern, url) is not None

    def _is_valid_image_url(self, url: str) -> bool:
        """이미지 URL 형식 검증"""
        if not self._is_valid_url(url):
            return False
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
        return any(url.lower().endswith(ext) for ext in image_extensions)

    def _is_valid_json(self, data: Any) -> bool:
        """JSON 데이터 유효성 검증"""
        if isinstance(data, (dict, list)):
            return True
        if isinstance(data, str):
            try:
                json.loads(data)
                return True
            except:
                return False
        return False

    def _is_valid_date(self, date_value: Any) -> bool:
        """날짜 형식 유효성 검증"""
        if isinstance(date_value, datetime):
            return True
        if isinstance(date_value, str):
            try:
                datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                return True
            except:
                return False
        return False

    def _get_province_from_coordinates(self, lat: float, lng: float) -> str | None:
        """좌표로부터 대략적인 도/시 추정"""
        # 간단한 좌표 기반 지역 추정 (실제로는 더 정확한 지역 경계 데이터 필요)
        if 37.4 <= lat <= 37.7 and 126.7 <= lng <= 127.2:
            return "서울특별시"
        elif 35.0 <= lat <= 35.3 and 128.9 <= lng <= 129.3:
            return "부산광역시"
        elif 35.8 <= lat <= 36.0 and 128.5 <= lng <= 128.7:
            return "대구광역시"
        # 더 많은 지역 추가 가능
        return None

    def _get_quality_grade(self, score: float) -> str:
        """품질 점수를 등급으로 변환"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_quality_recommendations(
        self, scores: dict[str, float], details: dict[str, Any]
    ) -> list[str]:
        """품질 개선 권장사항 생성"""
        recommendations = []

        # 완성도 개선
        if scores["completeness"] < 80:
            missing_required = details["completeness"].get("missing_required", [])
            if missing_required:
                recommendations.append(
                    f"필수 필드 입력 필요: {', '.join(missing_required)}"
                )

            missing_optional = details["completeness"].get("missing_optional", [])
            if len(missing_optional) > 3:
                recommendations.append(
                    "선택 필드를 더 많이 채워서 정보 완성도를 높이세요"
                )

        # 정확성 개선
        if scores["accuracy"] < 80:
            accuracy_issues = details["accuracy"].get("issues", [])
            for issue in accuracy_issues[:3]:  # 최대 3개만 표시
                recommendations.append(f"정확성 개선: {issue}")

        # 일관성 개선
        if scores["consistency"] < 80:
            consistency_issues = details["consistency"].get("issues", [])
            for issue in consistency_issues[:2]:  # 최대 2개만 표시
                recommendations.append(f"일관성 개선: {issue}")

        # 유효성 개선
        if scores["validity"] < 80:
            validity_issues = details["validity"].get("issues", [])
            for issue in validity_issues[:2]:  # 최대 2개만 표시
                recommendations.append(f"유효성 개선: {issue}")

        # 최신성 개선
        if scores["freshness"] < 60:
            recommendations.append("데이터 업데이트가 필요합니다")

        if not recommendations:
            recommendations.append("데이터 품질이 우수합니다!")

        return recommendations


def calculate_and_update_quality_scores(
    db: Session, table_name: str, limit: int = 100
) -> dict[str, Any]:
    """
    테이블의 데이터 품질 점수를 계산하고 업데이트

    Args:
        db: 데이터베이스 세션
        table_name: 대상 테이블명
        limit: 처리할 레코드 수 제한

    Returns:
        Dict containing processing results
    """
    analyzer = DataQualityAnalyzer(db)

    # 테이블별 쿼리 정의
    table_queries = {
        "destinations": """
            SELECT destination_id, name, province, region, category, 
                   latitude, longitude, amenities, image_url, rating,
                   created_at, updated_at
            FROM destinations 
            ORDER BY updated_at DESC 
            LIMIT :limit
        """,
        "restaurants": """
            SELECT content_id, restaurant_name, region_code, cuisine_type,
                   address, latitude, longitude, tel, homepage, operating_hours,
                   created_at, updated_at, last_sync_at
            FROM restaurants 
            ORDER BY updated_at DESC 
            LIMIT :limit
        """,
        "accommodations": """
            SELECT destination_id as content_id, name, province as region_code, category as type, 
                   NULL as address, latitude, longitude, 
                   CASE WHEN amenities ? 'tel' THEN amenities->>'tel' ELSE NULL END as phone,
                   rating, amenities, created_at, NULL as updated_at, NULL as last_sync_at
            FROM destinations 
            WHERE category = '숙박'
            ORDER BY created_at DESC 
            LIMIT :limit
        """
    }

    if table_name not in table_queries:
        raise ValueError(f"지원하지 않는 테이블: {table_name}")

    try:
        # 데이터 조회
        query = text(table_queries[table_name])
        result = db.execute(query, {"limit": limit})
        records = result.fetchall()

        processed_count = 0
        quality_scores = []

        for record in records:
            # 레코드를 딕셔너리로 변환
            record_dict = dict(record._mapping)

            # 품질 점수 계산
            quality_result = analyzer.calculate_destination_quality_score(record_dict)

            # 품질 점수 업데이트
            if table_name == "destinations":
                update_query = text(
                    """
                    UPDATE destinations 
                    SET data_quality_score = :score
                    WHERE destination_id = :id
                """
                )
                db.execute(
                    update_query,
                    {
                        "score": quality_result["total_score"],
                        "id": record_dict["destination_id"],
                    },
                )
            else:
                update_query = text(
                    f"""
                    UPDATE {table_name} 
                    SET data_quality_score = :score
                    WHERE content_id = :id
                """
                )
                db.execute(
                    update_query,
                    {
                        "score": quality_result["total_score"],
                        "id": record_dict["content_id"],
                    },
                )

            quality_scores.append(quality_result["total_score"])
            processed_count += 1

        db.commit()

        # 통계 계산
        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        grade_distribution = {}

        for score in quality_scores:
            grade = analyzer._get_quality_grade(score)
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

        return {
            "success": True,
            "processed_count": processed_count,
            "average_score": round(avg_score, 2),
            "score_range": {
                "min": min(quality_scores) if quality_scores else 0,
                "max": max(quality_scores) if quality_scores else 0,
            },
            "grade_distribution": grade_distribution,
            "table_name": table_name,
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e), "processed_count": 0}
