import hashlib
from decimal import Decimal

from .config import MANHATTAN_BBOX


# is_manhattan: 判断坐标是否在曼哈顿边界框内
# 参数：lat(纬度), lng(经度)
# 返回：bool，坐标在 MANHATTAN_BBOX 范围内返回 True
def is_manhattan(lat, lng):
    return (
        MANHATTAN_BBOX["lat_min"] <= float(lat) <= MANHATTAN_BBOX["lat_max"]
        and MANHATTAN_BBOX["lng_min"] <= float(lng) <= MANHATTAN_BBOX["lng_max"]
    )


# gps_to_district: 将 GPS 坐标粗略映射到曼哈顿区域
# 按纬度/经度阈值划分为 uptown / midtown_east / midtown_west / downtown
# 参数：lat(纬度), lng(经度)
# 返回：str，区域名称
def gps_to_district(lat, lng):
    lat, lng = float(lat), float(lng)
    if lat > 40.800:
        return "uptown"
    if lat > 40.750:
        return "midtown_east" if lng > -73.975 else "midtown_west"
    return "downtown"


# source_hash: 用管道符拼接字段后取 SHA-256 前 36 位作为去重指纹
# 参数：*parts，任意数量的可哈希字段，空值跳过
# 返回：str，36 位十六进制哈希字符串
def source_hash(*parts):
    payload = "|".join(str(part) for part in parts if part)
    return hashlib.sha256(payload.encode()).hexdigest()[:36]


# gen_vid: 根据数据源名称和原始 ID 生成唯一 venue ID（source_hash 封装）
# 参数：source(数据来源标识), source_id(原始记录 ID)
# 返回：str，36 位十六进制哈希字符串
def gen_vid(source, source_id):
    return source_hash(source, source_id)


# safe_int: 安全转换为整数，失败返回 None
# 参数：value(待转换值)
# 返回：int | None
def safe_int(value):
    try:
        return int(float(str(value).strip())) if value and str(value).strip() else None
    except (ValueError, TypeError, OverflowError):
        return None


# safe_dec: 安全转换为 Decimal，适用于精确小数运算
# 参数：value(待转换值)
# 返回：Decimal | None
def safe_dec(value):
    try:
        return Decimal(str(value).strip()) if value and str(value).strip() else None
    except (ValueError, TypeError, ArithmeticError):
        return None


# validate_coords: 校验经纬度是否在指定边界框内
# 参数：lat(纬度), lng(经度), bbox(含 lat_min/lat_max/lng_min/lng_max 的字典)
# 返回：bool
def validate_coords(lat, lng, bbox):
    try:
        lat_value, lng_value = float(lat), float(lng)
    except (ValueError, TypeError):
        return False
    return (
        bbox["lat_min"] <= lat_value <= bbox["lat_max"]
        and bbox["lng_min"] <= lng_value <= bbox["lng_max"]
    )


# check_row: 检查数据行必填字段是否齐全且非空
# 参数：row(一行数据字典), required_fields(必填字段名列表)
# 返回：bool，所有必填字段存在且非空返回 True
def check_row(row, required_fields):
    return all(str(row.get(field, "") or "").strip() for field in required_fields)


# fill_missing: 值为 None 或空字符串时替换为默认值
# 参数：value(原始值), default(替代值，默认 None)
# 返回：与 value 同类型或 default 类型
def fill_missing(value, default=None):
    return value if value not in (None, "") else default
