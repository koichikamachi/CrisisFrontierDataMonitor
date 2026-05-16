"""OECD SDMX 2.1 (sdmx.oecd.org) から系列を取得して SQLite に保存するスクリプト。

責務：取得と保存のみ。描画やHTML出力は行わない。
fetch_data.py / fetch_worldbank.py / fetch_imf.py と同じ DB スキーマ（observations）に書き込む。
indicators.yaml の data_sources（source == "oecd"）を読む。

series_id は "{agency},{dataflow}/{key}" 形式
（例: OECD.SDD.TPS,DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL/JPN.M.N.CPI.IX._T.N._Z）。
エージェンシーをカンマでデータフローと分離する点が IMF/BIS と異なる。

レスポンスは SDMX-JSON 1.0 形式（json.loads で処理）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "indicators.yaml"
DB_PATH = PROJECT_ROOT / "data" / "crisis_frontier.db"

OECD_BASE = "https://sdmx.oecd.org/public/rest"
START_PERIOD = "1990"
HTTP_TIMEOUT_SEC = 90
RETRY_WAIT_SEC = 2.0
INTER_REQUEST_PAUSE_SEC = 0.5
USER_AGENT = "CrisisFrontierDataMonitor/0.3"
ACCEPT_HEADER = "application/vnd.sdmx.data+json; charset=utf-8; version=1.0"


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


def parse_series_id(series_id: str) -> tuple[str, str, str]:
    """'OECD.SDD.TPS,DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL/JPN.M.N.CPI.IX._T.N._Z'
    → ('OECD.SDD.TPS', 'DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL', 'JPN.M.N.CPI.IX._T.N._Z')

    OECD は IMF/BIS と違いエージェンシーが複数あるため、series_id にエージェンシーを含める。
    """
    if "," not in series_id or "/" not in series_id:
        raise ValueError(
            f"series_id は '{{agency}},{{dataflow}}/{{key}}' 形式で記述してください: {series_id!r}"
        )
    agency_dataflow, key = series_id.split("/", 1)
    if "," not in agency_dataflow:
        raise ValueError(
            f"series_id にエージェンシーが含まれていません: {series_id!r}"
        )
    agency, dataflow = agency_dataflow.split(",", 1)
    return agency, dataflow, key


def build_url(agency: str, dataflow: str, key: str, end_year: int) -> str:
    return (
        f"{OECD_BASE}/data/{agency},{dataflow}/{key}"
        f"?startPeriod={START_PERIOD}&endPeriod={end_year}"
    )


def fetch_json(url: str) -> dict:
    """1回だけ再試行してから本格失敗扱い。fetch_imf.py の fetch_xml と同形。"""
    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": ACCEPT_HEADER,
                    "User-Agent": USER_AGENT,
                },
            )
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            # 4xx は再試行しても無駄
            if 400 <= e.code < 500:
                raise
            last_err = e
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
        if attempt == 1:
            time.sleep(RETRY_WAIT_SEC)
    assert last_err is not None
    raise last_err


def normalize_period(time_period: str) -> str:
    """SDMX-JSON の '1990-01' などを 'YYYY-MM-DD' へ。月次は月初日に揃える。

    OECD は '1990-01' 形式（IMF の '1990-M01' とは異なる）。
    四半期/年次が必要になればここを拡張する。
    """
    if len(time_period) == 7 and time_period[4] == "-":
        year, month = time_period.split("-")
        return f"{int(year):04d}-{int(month):02d}-01"
    raise ValueError(f"未対応の TIME_PERIOD 形式: {time_period!r}")


def parse_observations(j: dict) -> list[tuple[str, float]]:
    """SDMX-JSON 1.0 構造から (date, value) のリストを返す。

    構造:
      data.dataSets[*].series[series_key].observations[idx_str] = [value, status_idx, ...]
      data.structure.dimensions.observation[0].values[idx] = {id: "1990-01", ...}

    observations の key は文字列化された整数で、observation 次元の values 配列への
    インデックスとなる。value が null の観測はスキップする。
    """
    rows: list[tuple[str, float]] = []
    data = j.get("data", {})
    datasets = data.get("dataSets", [])
    if not datasets:
        return rows
    structure = data.get("structure", {})
    obs_dims = structure.get("dimensions", {}).get("observation", [])
    if not obs_dims:
        return rows
    time_vals = obs_dims[0].get("values", [])

    for ds in datasets:
        series_dict = ds.get("series", {})
        for series_key, series in series_dict.items():
            for idx_str, obs in series.get("observations", {}).items():
                if not isinstance(obs, list) or not obs:
                    continue
                val = obs[0]
                if val is None:
                    continue
                try:
                    idx = int(idx_str)
                    if idx < 0 or idx >= len(time_vals):
                        continue
                    time_period = time_vals[idx].get("id")
                    if not time_period:
                        continue
                    date_str = normalize_period(time_period)
                    rows.append((date_str, float(val)))
                except (ValueError, KeyError, IndexError):
                    continue

    rows.sort(key=lambda r: r[0])
    return rows


def save_observations(
    conn: sqlite3.Connection,
    country_id: str,
    indicator_id: str,
    rows: list[tuple[str, float]],
) -> int:
    if not rows:
        return 0
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = [
        (country_id, indicator_id, date_str, value, "OECD SDMX", retrieved_at)
        for (date_str, value) in rows
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO observations
            (country_id, indicator_id, date, value, source_name, retrieved_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    conn.commit()
    return len(payload)


def fetch_one(conn: sqlite3.Connection, entry: dict) -> tuple[bool, str]:
    country_id = entry["country_id"]
    indicator_id = entry["indicator_id"]
    series_id = entry["series_id"]
    end_year = datetime.now(timezone.utc).year + 1
    try:
        agency, dataflow, key = parse_series_id(series_id)
        url = build_url(agency, dataflow, key, end_year)
        j = fetch_json(url)
        rows = parse_observations(j)
        if not rows:
            return False, f"[{country_id}/{indicator_id}] {series_id}: 取得件数0"
        n = save_observations(conn, country_id, indicator_id, rows)
        return True, f"[{country_id}/{indicator_id}] {series_id}: {n}件保存"
    except urllib.error.HTTPError as e:
        return False, f"[{country_id}/{indicator_id}] {series_id}: HTTP{e.code} - {e.reason}"
    except urllib.error.URLError as e:
        return False, f"[{country_id}/{indicator_id}] {series_id}: 通信失敗 - {e.reason!r}"
    except json.JSONDecodeError as e:
        return False, f"[{country_id}/{indicator_id}] {series_id}: JSON解析失敗 - {e}"
    except Exception as e:
        return False, f"[{country_id}/{indicator_id}] {series_id}: 取得失敗 - {e!r}"


def main() -> int:
    config = load_config()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    oecd_entries = [
        e for e in config.get("data_sources", []) if e.get("source") == "oecd"
    ]
    if not oecd_entries:
        print("OECD SDMX 経由の data_sources はありません。スキップ。")
        return 0

    conn = sqlite3.connect(DB_PATH)
    try:
        init_schema(conn)
        success = 0
        failure = 0
        for entry in oecd_entries:
            ok, msg = fetch_one(conn, entry)
            print(msg)
            if ok:
                success += 1
            else:
                failure += 1
            time.sleep(INTER_REQUEST_PAUSE_SEC)

        print(f"取得完了: 成功 {success} / 失敗 {failure}")
        return 0 if success > 0 else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
