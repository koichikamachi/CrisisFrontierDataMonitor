"""IMF SDMX 2.1 (api.imf.org) から系列を取得して SQLite に保存するスクリプト。

責務：取得と保存のみ。描画やHTML出力は行わない。
fetch_data.py / fetch_worldbank.py と同じ DB スキーマ（observations）に書き込む。
indicators.yaml の data_sources（source == "imf"）を読む。

series_id は "{dataflow}/{key}" 形式（例: MFS_IR/THA.DISR_RT_PT_A_PT.M）。
レスポンスは SDMX 2.1 StructureSpecificData XML 形式。
OBS_VALUE 属性が無い観測（メタのみで実値未投入）はスキップする。
"""
from __future__ import annotations

import sqlite3
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "indicators.yaml"
DB_PATH = PROJECT_ROOT / "data" / "crisis_frontier.db"

IMF_BASE = "https://api.imf.org/external/sdmx/2.1"
IMF_AGENCY = "IMF.STA"
START_PERIOD = "1990"
HTTP_TIMEOUT_SEC = 90  # IMF SDMX はやや応答が遅い
RETRY_WAIT_SEC = 2.0
INTER_REQUEST_PAUSE_SEC = 0.5
USER_AGENT = "CrisisFrontierDataMonitor/0.2"


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


def parse_series_id(series_id: str) -> tuple[str, str]:
    """'MFS_IR/THA.DISR_RT_PT_A_PT.M' → ('MFS_IR', 'THA.DISR_RT_PT_A_PT.M')"""
    if "/" not in series_id:
        raise ValueError(
            f"series_id は '{{dataflow}}/{{key}}' 形式で記述してください: {series_id!r}"
        )
    dataflow, key = series_id.split("/", 1)
    return dataflow, key


def build_url(dataflow: str, key: str, end_year: int) -> str:
    return (
        f"{IMF_BASE}/data/{IMF_AGENCY},{dataflow}/{key}"
        f"?startPeriod={START_PERIOD}&endPeriod={end_year}"
    )


def fetch_xml(url: str) -> str:
    """1回だけ再試行してから本格失敗扱い。"""
    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/xml",
                    "User-Agent": USER_AGENT,
                },
            )
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
                return resp.read().decode("utf-8")
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
    """SDMX の '1990-M01' などを 'YYYY-MM-DD' へ。月次は月初日に揃える。

    現状は月次のみを扱う前提。四半期/年次が必要になればここを拡張する。
    """
    if "-M" in time_period:
        year, month = time_period.split("-M", 1)
        return f"{int(year):04d}-{int(month):02d}-01"
    # 年次（"YYYY"）や四半期（"YYYY-Q1"）が来た場合は今は未対応として例外
    raise ValueError(f"未対応の TIME_PERIOD 形式: {time_period!r}")


def parse_observations(xml_body: str) -> list[tuple[str, float]]:
    """SDMX 2.1 StructureSpecificData XML から (date, value) のリストを返す。

    OBS_VALUE 属性が無い観測（メタのみで実値未投入）はスキップする。
    namespace に依存しない走査（local name でマッチ）。
    """
    rows: list[tuple[str, float]] = []
    root = ET.fromstring(xml_body)

    for elem in root.iter():
        local = elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag
        if local != "Obs":
            continue
        time_period = elem.attrib.get("TIME_PERIOD")
        obs_value = elem.attrib.get("OBS_VALUE")
        if time_period is None or obs_value is None or obs_value == "":
            # 値未投入の観測はスキップ
            continue
        try:
            date_str = normalize_period(time_period)
            value = float(obs_value)
        except ValueError:
            continue
        rows.append((date_str, value))

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
        (country_id, indicator_id, date_str, value, "IMF SDMX", retrieved_at)
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
    end_year = datetime.now(timezone.utc).year + 1  # 余裕を持たせる
    try:
        dataflow, key = parse_series_id(series_id)
        url = build_url(dataflow, key, end_year)
        xml_body = fetch_xml(url)
        rows = parse_observations(xml_body)
        if not rows:
            return False, f"[{country_id}/{indicator_id}] {series_id}: 取得件数0"
        n = save_observations(conn, country_id, indicator_id, rows)
        return True, f"[{country_id}/{indicator_id}] {series_id}: {n}件保存"
    except urllib.error.HTTPError as e:
        return False, f"[{country_id}/{indicator_id}] {series_id}: HTTP{e.code} - {e.reason}"
    except urllib.error.URLError as e:
        return False, f"[{country_id}/{indicator_id}] {series_id}: 通信失敗 - {e.reason!r}"
    except ET.ParseError as e:
        return False, f"[{country_id}/{indicator_id}] {series_id}: XML解析失敗 - {e}"
    except Exception as e:
        return False, f"[{country_id}/{indicator_id}] {series_id}: 取得失敗 - {e!r}"


def main() -> int:
    config = load_config()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    imf_entries = [
        e for e in config.get("data_sources", []) if e.get("source") == "imf"
    ]
    if not imf_entries:
        print("IMF SDMX 経由の data_sources はありません。スキップ。")
        return 0

    conn = sqlite3.connect(DB_PATH)
    try:
        init_schema(conn)
        success = 0
        failure = 0
        for entry in imf_entries:
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
