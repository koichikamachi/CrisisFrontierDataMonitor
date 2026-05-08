"""FREDから系列を取得してSQLiteに保存するスクリプト。

責務：取得と保存のみ。描画やHTML出力は行わない。
indicators.yaml の data_sources（source == "fred"）を読む。
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from fredapi import Fred

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "indicators.yaml"
DB_PATH = PROJECT_ROOT / "data" / "crisis_frontier.db"
ENV_PATH = PROJECT_ROOT / ".env"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_fred_client() -> Fred:
    load_dotenv(ENV_PATH)
    api_key = os.getenv("FRED_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise RuntimeError(
            "FRED_API_KEY が設定されていません。"
            ".env に FRED_API_KEY=xxxx を書いてください。"
        )
    return Fred(api_key=api_key)


def init_schema(conn: sqlite3.Connection) -> None:
    """observations テーブルのみを最低限維持する。
    旧 indicators / countries マスタテーブルは新仕様では yaml が正本のため使わない。
    """
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


def save_observations(
    conn: sqlite3.Connection,
    country_id: str,
    indicator_id: str,
    series: pd.Series,
    source_name: str,
) -> int:
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for ts, val in series.items():
        value = None if pd.isna(val) else float(val)
        date_str = pd.Timestamp(ts).strftime("%Y-%m-%d")
        rows.append(
            (country_id, indicator_id, date_str, value, source_name, retrieved_at)
        )
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


def fetch_one(
    fred: Fred,
    conn: sqlite3.Connection,
    entry: dict,
    start_date: str,
) -> tuple[bool, str]:
    country_id = entry["country_id"]
    indicator_id = entry["indicator_id"]
    code = entry["series_id"]
    try:
        series = fred.get_series(code, observation_start=start_date)
        if series is None or len(series) == 0:
            return False, f"[{country_id}/{indicator_id}] {code}: 取得件数0"
        n = save_observations(conn, country_id, indicator_id, series, "FRED")
        return True, f"[{country_id}/{indicator_id}] {code}: {n}件保存"
    except Exception as e:
        return False, f"[{country_id}/{indicator_id}] {code}: 取得失敗 - {e!r}"


def main() -> int:
    config = load_config()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    fred = get_fred_client()
    conn = sqlite3.connect(DB_PATH)
    try:
        init_schema(conn)

        start_date = config["fetch_settings"]["start_date"]
        # FRED系列のみ処理（worldbank等は別スクリプトに委譲）
        fred_entries = [
            e for e in config["data_sources"] if e.get("source") == "fred"
        ]

        success = 0
        failure = 0
        for entry in fred_entries:
            ok, msg = fetch_one(fred, conn, entry, start_date)
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
