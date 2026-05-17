"""SQLiteから観測値を読み出してPNGを生成するスクリプト。

責務：描画のみ。取得もHTML出力も行わない。
data_sources の各エントリにつき1枚のPNGを生成する。
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "indicators.yaml"
DB_PATH = PROJECT_ROOT / "data" / "crisis_frontier.db"
# 仕様 3.6 のディレクトリ構成に従い、PNG は outputs/html/images/ 配下に出力
IMG_DIR = PROJECT_ROOT / "outputs" / "html" / "images"

# 日本語フォント設定（Windows 11同梱フォントを優先順に指定）
matplotlib.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

SOURCE_LABELS = {
    "fred": "FRED",
    "worldbank": "World Bank",
}

# 国名表示（チャートタイトル用）
COUNTRY_NAMES = {
    "jp": "日本",
    "us": "米国",
    "th": "タイ",
    "kr": "韓国",
    "id": "インドネシア",
    "my": "マレーシア",
}


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_observations(
    conn: sqlite3.Connection, country_id: str, indicator_id: str
) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT date, value
          FROM observations
         WHERE country_id = ? AND indicator_id = ?
         ORDER BY date ASC
        """,
        conn,
        params=(country_id, indicator_id),
        parse_dates=["date"],
    )


def build_chart(
    df: pd.DataFrame,
    country_name: str,
    indicator_label: str,
    series_code: str,
    source_label: str,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    ax.plot(df["date"], df["value"], linewidth=1.0)
    ax.set_title(f"{country_name} - {indicator_label}", fontsize=14)
    ax.set_xlabel("年")
    ax.set_ylabel("")
    ax.grid(True, linestyle="--", alpha=0.4)

    today = datetime.now().strftime("%Y-%m-%d")
    footer = f"Source: {source_label} ({series_code})  /  Retrieved: {today}"
    fig.text(0.99, 0.01, footer, ha="right", va="bottom", fontsize=8, color="gray")

    fig.tight_layout(rect=[0, 0.03, 1, 1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)


def main() -> int:
    config = load_config()
    indicators = {ind["id"]: ind for ind in config["indicators_global"]}

    if not DB_PATH.exists():
        print(f"DBが見つかりません: {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        success = 0
        failure = 0
        for entry in config["data_sources"]:
            country_id = entry["country_id"]
            indicator_id = entry["indicator_id"]
            code = entry["series_id"]
            source_key = entry.get("source", "fred")
            source_label = SOURCE_LABELS.get(source_key, source_key)
            try:
                df = fetch_observations(conn, country_id, indicator_id)
                if df.empty:
                    print(f"[{country_id}/{indicator_id}] {code}: 観測値なし、スキップ")
                    failure += 1
                    continue
                df = df.dropna(subset=["value"])
                country_name = COUNTRY_NAMES.get(country_id, country_id)
                indicator_label = indicators[indicator_id]["label"]
                output_path = IMG_DIR / f"{country_id}_{indicator_id}.png"
                build_chart(
                    df, country_name, indicator_label, code, source_label, output_path,
                )
                print(f"[{country_id}/{indicator_id}] {code}: {output_path.name} 生成")
                success += 1
            except Exception as e:
                print(
                    f"[{country_id}/{indicator_id}] {code}: 描画失敗 - {e!r}",
                    file=sys.stderr,
                )
                failure += 1

        print(f"描画完了: 成功 {success} / 失敗 {failure}")
        return 0 if success > 0 else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
