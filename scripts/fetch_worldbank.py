"""World Bank APIから系列を取得してSQLiteに保存するスクリプト。

責務：取得と保存のみ。描画やHTML出力は行わない。
fetch_data.py と同じ DB スキーマ（observations）に書き込む。
indicators.yaml の data_sources（source == "worldbank"）を読む。
"""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "indicators.yaml"
DB_PATH = PROJECT_ROOT / "data" / "crisis_frontier.db"

WB_API_BASE = "https://api.worldbank.org/v2"
WB_PER_PAGE = 100
WB_MRV = 60  # 直近60年
HTTP_TIMEOUT_SEC = 30


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def init_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS observations (
            country_id    TEXT NOT NULL,
            indicator_id  TEXT NOT NULL,
            date          TEXT NOT NULL,
            value         REAL,
            source_name   TEXT,
            retrieved_at  TEXT NOT NULL,
            PRIMARY KEY (country_id, indicator_id, date)
        );

        CREATE INDEX IF NOT EXISTS idx_obs_ind_date
            ON observations (indicator_id, country_id, date);
        """
    )
    conn.commit()


def fetch_worldbank_json(country_iso2: str, wb_indicator: str) -> list[dict]:
    url = (
        f"{WB_API_BASE}/country/{country_iso2}/indicator/{wb_indicator}"
        f"?format=json&per_page={WB_PER_PAGE}&mrv={WB_MRV}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "CrisisFrontierDataMonitor/0.2"},
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
        body = resp.read().decode("utf-8")
    payload = json.loads(body)
    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError(f"想定外の応答形式: {payload!r}")
    data = payload[1]
    if not isinstance(data, list):
        raise RuntimeError(f"data部が配列ではありません: {data!r}")
    return data


def save_observations(
    conn: sqlite3.Connection,
    country_id: str,
    indicator_id: str,
    data: list[dict],
) -> int:
    """年次データを (date='YYYY-12-31', value) で保存。"""
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for rec in data:
        year = rec.get("date")
        if not year:
            continue
        date_str = f"{year}-12-31"
        raw = rec.get("value")
        value = None if raw is None else float(raw)
        rows.append(
            (country_id, indicator_id, date_str, value, "World Bank", retrieved_at)
        )
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR REPLACE INTO observations
            (country_id, indicator_id, date, value, source_name, retrieved_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def fetch_one(conn: sqlite3.Connection, entry: dict) -> tuple[bool, str]:
    country_id = entry["country_id"]
    indicator_id = entry["indicator_id"]
    code = entry["series_id"]
    # World Bank は ISO 3166-1 alpha-2 大文字が標準
    country_iso2 = country_id.upper()
    try:
        data = fetch_worldbank_json(country_iso2, code)
        if not data:
            return False, f"[{country_id}/{indicator_id}] {code}: 取得件数0"
        n = save_observations(conn, country_id, indicator_id, data)
        return True, f"[{country_id}/{indicator_id}] {code}: {n}件保存"
    except urllib.error.HTTPError as e:
        return False, f"[{country_id}/{indicator_id}] {code}: HTTP{e.code} - {e.reason}"
    except urllib.error.URLError as e:
        return False, f"[{country_id}/{indicator_id}] {code}: 通信失敗 - {e.reason!r}"
    except Exception as e:
        return False, f"[{country_id}/{indicator_id}] {code}: 取得失敗 - {e!r}"


def main() -> int:
    config = load_config()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    wb_entries = [
        e for e in config["data_sources"] if e.get("source") == "worldbank"
    ]
    if not wb_entries:
        print("World Bank 経由の data_sources はありません。スキップ。")
        return 0

    conn = sqlite3.connect(DB_PATH)
    try:
        init_schema(conn)
        success = 0
        failure = 0
        for entry in wb_entries:
            ok, msg = fetch_one(conn, entry)
            print(msg)
            if ok:
                success += 1
            else:
                failure += 1

        print(f"取得完了: 成功 {success} / 失敗 {failure}")
        return 0 if success > 0 else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
