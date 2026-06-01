from __future__ import annotations

import re
from dataclasses import dataclass

from backend.core.text import normalize_text


PACKING_BUFFER_MINUTES = 30
MAX_AREAS_IN_ANSWER = 3


@dataclass(frozen=True)
class DeliveryAreaEstimate:
    name: str
    travel_minutes: tuple[int, int]
    aliases: tuple[str, ...]


DELIVERY_AREA_ESTIMATES: tuple[DeliveryAreaEstimate, ...] = (
    DeliveryAreaEstimate(
        name="Nam Từ Liêm",
        travel_minutes=(10, 20),
        aliases=(
            "nam tu liem",
            "my dinh",
            "me tri",
            "phu do",
            "trung van",
            "dai mo",
            "tay mo",
            "xuan phuong",
            "le duc tho",
            "ham nghi",
            "nguyen co thach",
            "do duc duc",
            "pham hung nam tu liem",
        ),
    ),
    DeliveryAreaEstimate(
        name="Bắc Từ Liêm",
        travel_minutes=(15, 25),
        aliases=("bac tu liem", "co nhue", "xuan dinh", "phu dien", "duc thang", "thuy phuong"),
    ),
    DeliveryAreaEstimate(
        name="Cầu Giấy",
        travel_minutes=(15, 25),
        aliases=(
            "cau giay",
            "dich vong",
            "nghia do",
            "nghia tan",
            "yen hoa",
            "trung hoa",
            "mai dich",
            "quan hoa",
            "tran thai tong",
            "duy tan",
            "ton that thuyet",
            "pham van bach",
            "xuan thuy",
            "ho tung mau",
            "nguyen khang",
            "pham hung cau giay",
        ),
    ),
    DeliveryAreaEstimate(
        name="Thanh Xuân",
        travel_minutes=(20, 30),
        aliases=(
            "thanh xuan",
            "nga tu so",
            "royal city",
            "khuat duy tien",
            "nguyen trai thanh xuan",
            "quan nhan",
            "vu trong phung",
            "nguyen tuan",
            "le van luong thanh xuan",
        ),
    ),
    DeliveryAreaEstimate(
        name="Hà Đông",
        travel_minutes=(20, 35),
        aliases=("ha dong", "mo lao", "van quan", "van phuc", "duong noi", "nguyen trai ha dong"),
    ),
    DeliveryAreaEstimate(
        name="Đống Đa",
        travel_minutes=(25, 35),
        aliases=("dong da", "thai ha", "lang ha", "cat linh", "o cho dua", "phuong mai", "kham thien", "ton duc thang"),
    ),
    DeliveryAreaEstimate(
        name="Ba Đình",
        travel_minutes=(25, 35),
        aliases=("ba dinh", "kim ma", "doi can", "lieu giai", "giang vo", "ngoc ha", "hoang hoa tham"),
    ),
    DeliveryAreaEstimate(
        name="Tây Hồ",
        travel_minutes=(30, 40),
        aliases=("tay ho", "xuan la", "au co", "nhat tan", "quang an", "tu lien", "lac long quan"),
    ),
    DeliveryAreaEstimate(
        name="Hoàn Kiếm",
        travel_minutes=(35, 45),
        aliases=("hoan kiem", "pho co", "hang ma", "hang bong", "hang bai", "trang tien", "ly thai to"),
    ),
    DeliveryAreaEstimate(
        name="Hai Bà Trưng",
        travel_minutes=(35, 50),
        aliases=("hai ba trung", "bach khoa", "minh khai", "bach mai", "pho hue", "vinh tuy", "times city"),
    ),
    DeliveryAreaEstimate(
        name="Hoàng Mai",
        travel_minutes=(40, 55),
        aliases=("hoang mai", "linh dam", "giai phong", "dinh cong", "giap bat", "yen so", "tan mai"),
    ),
    DeliveryAreaEstimate(
        name="Long Biên",
        travel_minutes=(45, 60),
        aliases=("long bien", "ngoc lam", "bo de", "viet hung", "sai dong", "aeon long bien"),
    ),
)

DELIVERY_AREA_NAMES = tuple(area.name for area in DELIVERY_AREA_ESTIMATES)
DELIVERY_LOCATION_HINT_KEYWORDS: tuple[str, ...] = (
    "duong",
    "pho",
    "ngo",
    "ngach",
    "hem",
    "so",
    "toa",
    "toa nha",
    "chung cu",
    "kdt",
    "khu do thi",
    "phuong",
    "quan",
    "den",
    "toi",
    "ve",
)


def _contains_alias(normalized_query: str, alias: str) -> bool:
    normalized_alias = " ".join(normalize_text(alias).split())
    if not normalized_alias:
        return False

    if re.search(rf"(?<!\w){re.escape(normalized_alias)}(?!\w)", normalized_query):
        return True

    compact_query = normalized_query.replace(" ", "")
    compact_alias = normalized_alias.replace(" ", "")
    return len(compact_alias) >= 6 and compact_alias in compact_query


def extract_delivery_areas(query: str) -> list[DeliveryAreaEstimate]:
    normalized_query = " ".join(normalize_text(query).split())
    if not normalized_query:
        return []

    matches: list[DeliveryAreaEstimate] = []
    for area in DELIVERY_AREA_ESTIMATES:
        if any(_contains_alias(normalized_query, alias) for alias in area.aliases):
            matches.append(area)

    return matches


def find_delivery_area_by_name(area_name: str) -> DeliveryAreaEstimate | None:
    normalized_area_name = " ".join(normalize_text(area_name).split())
    if not normalized_area_name:
        return None

    for area in DELIVERY_AREA_ESTIMATES:
        if normalized_area_name == normalize_text(area.name):
            return area
        if any(normalized_area_name == normalize_text(alias) for alias in area.aliases):
            return area

    return None


def should_try_llm_delivery_area(query: str) -> bool:
    if re.search(r"\d", query):
        return True

    normalized_query = f" {' '.join(normalize_text(query).split())} "
    return any(f" {keyword} " in normalized_query for keyword in DELIVERY_LOCATION_HINT_KEYWORDS)


def _format_minutes_range(minutes: tuple[int, int]) -> str:
    start, end = minutes
    if start == end:
        return f"khoảng {start} phút"
    return f"khoảng {start}-{end} phút"


def build_delivery_eta_answer(
    query: str,
    *,
    area_hint: str | None = None,
    matched_text: str = "",
    source: str = "rule",
) -> str | None:
    areas = extract_delivery_areas(query)
    if not areas and area_hint:
        hinted_area = find_delivery_area_by_name(area_hint)
        if hinted_area:
            areas = [hinted_area]

    if not areas:
        return None

    parts: list[str] = []
    for area in areas[:MAX_AREAS_IN_ANSWER]:
        travel_start, travel_end = area.travel_minutes
        eta = (travel_start + PACKING_BUFFER_MINUTES, travel_end + PACKING_BUFFER_MINUTES)
        parts.append(
            f"{area.name}: di chuyển {_format_minutes_range(area.travel_minutes)}, "
            f"cộng 30 phút chuẩn bị = {_format_minutes_range(eta)}"
        )

    answer = "Shop xuất phát từ Nam Từ Liêm. "
    if source == "llm" and matched_text and len(areas) == 1:
        answer += f"Mình nhận diện địa chỉ \"{matched_text}\" thuộc {areas[0].name}. "

    answer += "; ".join(parts)
    if len(areas) > MAX_AREAS_IN_ANSWER:
        answer += f"; còn {len(areas) - MAX_AREAS_IN_ANSWER} khu vực khác bạn gửi mình tách riêng nhé"

    return answer + ". ETA là ước tính và có thể thay đổi theo thời tiết hoặc giờ cao điểm."
