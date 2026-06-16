"""fix_restroom_gps.py — 修复 124 个 (0,0) 坐标 restroom 的 GPS。

从 NYC Open Data Parks Toilets API 按名称匹配，更新 DB 中的 latitude/longitude。
然后重新分配 district。

用法:
    cd Data+ML/test/6.8-6.12_DB
    python dqr/fix_restroom_gps.py
"""

import sys
from pathlib import Path

try:
    from dqr_utils import get_conn, gps_to_district
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dqr_utils import get_conn, gps_to_district

import requests
import pymysql


def fix_restroom_gps():
    """从 NYC Open Data 匹配 GPS 并更新 DB。"""
    conn = get_conn()
    cur = conn.cursor()

    # 1. 获取 DB 中 (0,0) 的 restroom
    cur.execute("""
        SELECT venue_id, name FROM venues
        WHERE venue_type = 'restroom' AND latitude = 0
    """)
    zero_restrooms = cur.fetchall()
    print(f'Venues with (0,0): {len(zero_restrooms)}')

    if not zero_restrooms:
        print('Nothing to fix.')
        conn.close()
        return

    # 2. 从 NYC Open Data 拉取 Parks Toilets (含 GPS)
    url = 'https://data.cityofnewyork.us/resource/hjae-yuav.json'
    resp = requests.get(url, params={'$select': 'name,latitude,longitude', '$limit': 5000}, timeout=30)
    resp.raise_for_status()
    parks = resp.json()
    print(f'Parks Toilets from API: {len(parks)}')

    # 3. 按名称匹配并更新
    matched = 0
    for venue_id, name in zero_restrooms:
        for p in parks:
            if p.get('name') and name and p['name'].lower() in name.lower():
                lat = float(p['latitude'])
                lng = float(p['longitude'])
                if lat > 40 and lng < -70:  # 基本合理性检查
                    district = gps_to_district(lat, lng)
                    cur.execute("""
                        UPDATE venues SET latitude=%s, longitude=%s, district=%s
                        WHERE venue_id=%s
                    """, (lat, lng, district, venue_id))
                    matched += 1
                    break

    conn.commit()
    print(f'Matched & updated: {matched}/{len(zero_restrooms)}')

    # 4. 验证
    cur.execute("SELECT COUNT(*) FROM venues WHERE venue_type='restroom' AND latitude=0")
    remaining = cur.fetchone()[0]
    print(f'Remaining (0,0): {remaining}')

    cur.execute("SELECT COUNT(*) FROM venues WHERE district IS NOT NULL")
    total_with_district = cur.fetchone()[0]
    print(f'Total venues with district: {total_with_district}')

    cur.close()
    conn.close()


if __name__ == '__main__':
    fix_restroom_gps()
