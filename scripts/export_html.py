"""静的HTMLサイトを生成するスクリプト。

責務：HTML出力（およびCSVエクスポート）のみ。
indicators.yaml の三層構造を読み、以下を生成する。

  outputs/html/
    index.html                          トップ（国カタログ＋指標カタログ）
    {country_id}/index.html              国別ページ（jp / us / th）
    indicator/{indicator-id-hyphen}/index.html  指標横断ページ（6本）
    data-paths/index.html                再配信経路の説明
    css/site.css                          共通CSS（既存）
    images/, csv/                         （build_charts.py / 本スクリプトが生成）
"""
from __future__ import annotations

import csv
import html
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "indicators.yaml"
DB_PATH = PROJECT_ROOT / "data" / "crisis_frontier.db"
HTML_DIR = PROJECT_ROOT / "outputs" / "html"
# 仕様 3.6 のディレクトリ構成：images/ と csv/ は outputs/html/ 配下
IMG_DIR = HTML_DIR / "images"
CSV_DIR = HTML_DIR / "csv"

SOURCE_LABELS = {
    "fred": "FRED",
    "worldbank": "World Bank",
    "imf": "IMF SDMX",
    "oecd": "OECD SDMX",
    "bis": "BIS SDMX",
}

# 国メタ（日本語名と英名）
COUNTRIES = [
    {"id": "jp", "name_ja": "日本",         "name_en": "Japan"},
    {"id": "us", "name_ja": "米国",         "name_en": "United States"},
    {"id": "th", "name_ja": "タイ",         "name_en": "Thailand"},
    {"id": "kr", "name_ja": "韓国",         "name_en": "South Korea"},
    {"id": "id", "name_ja": "インドネシア", "name_en": "Indonesia"},
    {"id": "my", "name_ja": "マレーシア",   "name_en": "Malaysia"},
]
COUNTRY_BY_ID = {c["id"]: c for c in COUNTRIES}

# indicator_id を URL 用ハイフン形式に変換するマップ
# （central_bank_total_assets だけは仕様 3.6 で central-bank-balance-sheet を採用）
INDICATOR_URL_SLUG = {
    "fx_usd": "fx-usd",
    "policy_rate": "policy-rate",
    "bond_10y": "bond-10y",
    "cpi": "cpi",
    "fx_reserves": "fx-reserves",
    "central_bank_total_assets": "central-bank-balance-sheet",
}

# 米国×fx_usd の特例文言（判断事項③）
US_FX_USD_NOT_APPLICABLE = (
    "「対米ドル為替レート」は米国には適用されません。"
    "米国にとって自国通貨と米ドルは同一通貨です。"
    "米国の対外的な為替動向を観察したい場合は、ドルインデックス（DXY）等を別途参照ください。"
)


# =============================================================
# ヘルパ：設定読み込み
# =============================================================

def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def index_data_sources(data_sources: list[dict]) -> dict[tuple[str, str], dict]:
    """(country_id, indicator_id) -> エントリ辞書 の dict にする。"""
    return {(e["country_id"], e["indicator_id"]): e for e in data_sources}


# =============================================================
# DB アクセス
# =============================================================

def fetch_observations(
    conn: sqlite3.Connection, country_id: str, indicator_id: str
) -> list[tuple[str, float | None]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT date, value
          FROM observations
         WHERE country_id = ? AND indicator_id = ?
         ORDER BY date ASC
        """,
        (country_id, indicator_id),
    )
    return cur.fetchall()


def compute_summary(rows: list[tuple[str, float | None]]) -> dict | None:
    valid = [(d, v) for d, v in rows if v is not None]
    if not valid:
        return None
    values = [v for _, v in valid]
    latest_date, latest_value = valid[-1]
    return {
        "latest_date": latest_date,
        "latest": latest_value,
        "max": max(values),
        "min": min(values),
        "mean": sum(values) / len(values),
        "count": len(values),
    }


def write_csv(rows: list[tuple[str, float | None]], country_id: str, indicator_id: str) -> Path:
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = CSV_DIR / f"{country_id}_{indicator_id}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "value"])
        for d, v in rows:
            writer.writerow([d, "" if v is None else v])
    return csv_path


# =============================================================
# レンダリング・ヘルパ
# =============================================================

def fmt(value: float, digits: int = 4) -> str:
    return f"{value:,.{digits}f}"


def relpath_prefix(depth: int) -> str:
    """depth 階層分の '../' を返す。トップは ''、/jp/ は '../'、/indicator/fx-usd/ は '../../'。"""
    return "../" * depth


def render_layout(title: str, body_html: str, depth: int) -> str:
    """全ページ共通の外枠を返す。"""
    prefix = relpath_prefix(depth)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | Crisis Frontier Global Data Monitor</title>
<link rel="stylesheet" href="{prefix}css/site.css">
</head>
<body>
{body_html}
</body>
</html>
"""


def render_breadcrumb(items: list[tuple[str, str | None]]) -> str:
    """items は (ラベル, href または None) のリスト。最後の要素は href=None で現在地。"""
    parts = []
    for i, (label, href) in enumerate(items):
        if i > 0:
            parts.append('<span class="sep">/</span>')
        if href is None:
            parts.append(html.escape(label))
        else:
            parts.append(f'<a href="{html.escape(href)}">{html.escape(label)}</a>')
    return f'<nav class="breadcrumb">{"".join(parts)}</nav>'


def render_site_footer(depth: int) -> str:
    prefix = relpath_prefix(depth)
    return (
        '<footer class="site-footer">'
        f'<a href="{prefix}index.html">トップ</a> ／ '
        f'<a href="{prefix}data-paths/">データ取得経路</a> ／ '
        '<a href="https://bookkeepingwhisperer.org" rel="external">BKW研究所</a>'
        '</footer>'
    )


def render_summary_table(summary: dict) -> str:
    return (
        '<table class="summary">'
        '<tr><th>項目</th><th>値</th></tr>'
        f'<tr><th>最新値</th><td>{fmt(summary["latest"])} '
        f'<span class="meta">({html.escape(summary["latest_date"])})</span></td></tr>'
        f'<tr><th>最大値</th><td>{fmt(summary["max"])}</td></tr>'
        f'<tr><th>最小値</th><td>{fmt(summary["min"])}</td></tr>'
        f'<tr><th>平均値</th><td>{fmt(summary["mean"])}</td></tr>'
        f'<tr><th>件数</th><td>{summary["count"]:,}</td></tr>'
        '</table>'
    )


def render_indicator_card(indicator_def: dict, country_id: str | None = None) -> str:
    """description / source_note / how_to_read の三層カード。

    country_id を指定すると、indicator_def の以下のフィールドから
    対応する国向けの追加段落を取り出し、それぞれのレイヤ末尾に追記する。
      - source_note_country_specific:  { us|jp|th: "..." }
      - how_to_read_country_specific:  { us|jp|th: "..." }
    country_id=None（指標横断ページなど）の場合は追記なし、universal text のみ。
    """
    description = indicator_def["description"].strip()
    source_note = indicator_def["source_note"].strip()
    how_to_read = indicator_def["how_to_read"].strip()

    if country_id:
        sn_specific = indicator_def.get("source_note_country_specific") or {}
        extra_sn = sn_specific.get(country_id)
        if extra_sn:
            source_note = source_note + "\n\n" + extra_sn.strip()
        hr_specific = indicator_def.get("how_to_read_country_specific") or {}
        extra_hr = hr_specific.get(country_id)
        if extra_hr:
            how_to_read = how_to_read + "\n\n" + extra_hr.strip()

    return (
        '<div class="indicator-card">'
        '<div class="layer">'
        '<span class="layer-label">これは何か</span>'
        f'<div class="layer-body">{html.escape(description)}</div>'
        '</div>'
        '<div class="layer">'
        '<span class="layer-label">誰が出しているか</span>'
        f'<div class="layer-body">{html.escape(source_note)}</div>'
        '</div>'
        '<div class="layer">'
        '<span class="layer-label">どう読むか</span>'
        f'<div class="layer-body">{html.escape(how_to_read)}</div>'
        '</div>'
        '</div>'
    )


def render_indicator_block(
    indicator_def: dict,
    country: dict,
    data_entry: dict | None,
    rows: list[tuple[str, float | None]],
    depth: int,
    today: str,
) -> str:
    """1指標分のセクション（タイトル＋メタ＋画像＋小表＋CSV＋指標カード）を返す。

    data_entry が None の場合：
      - 米国×fx_usd は「対象外」プレースホルダ
      - それ以外は「収集予定」プレースホルダ
    """
    prefix = relpath_prefix(depth)
    indicator_id = indicator_def["id"]
    label = indicator_def["label"]

    title_html = (
        f'<h2>{indicator_def["display_order"]}. '
        f'{html.escape(label)} '
        f'<span class="meta">（{html.escape(indicator_id)}）</span></h2>'
    )

    parts = [title_html]

    if data_entry is None:
        # プレースホルダ
        if country["id"] == "us" and indicator_id == "fx_usd":
            parts.append(
                f'<div class="placeholder not-applicable">'
                f'{html.escape(US_FX_USD_NOT_APPLICABLE)}'
                f'</div>'
            )
        else:
            parts.append(
                '<div class="placeholder">'
                f'この指標（{html.escape(country["name_ja"])} / {html.escape(label)}）'
                'は今後収集予定です。'
                '</div>'
            )
        # 指標カードはプレースホルダでも表示する（観測マニュアルとしての意味があるため）
        parts.append(render_indicator_card(indicator_def, country["id"]))
        return f'<section class="indicator-block">{"".join(parts)}</section>'

    # データあり
    series_id = data_entry["series_id"]
    source_label = SOURCE_LABELS.get(data_entry.get("source", "fred"), data_entry.get("source", ""))
    frequency = data_entry.get("frequency", "")

    meta_text = (
        f'出典: {html.escape(source_label)} ({html.escape(series_id)}) ／ '
        f'頻度: {html.escape(frequency)} ／ '
        f'更新日: {html.escape(today)}'
    )
    parts.append(f'<p class="meta">{meta_text}</p>')

    img_name = f"{country['id']}_{indicator_id}.png"
    img_path = IMG_DIR / img_name
    if img_path.exists():
        parts.append(
            f'<img class="chart" src="{prefix}images/{html.escape(img_name)}" '
            f'alt="{html.escape(country["name_ja"])} {html.escape(label)}">'
        )
    else:
        parts.append(f'<p class="no-data">画像未生成: {html.escape(img_name)}</p>')

    summary = compute_summary(rows)
    if summary is not None:
        parts.append(render_summary_table(summary))
    else:
        parts.append('<p class="no-data">観測値がありません</p>')

    csv_name = f"{country['id']}_{indicator_id}.csv"
    parts.append(
        '<div class="actions">'
        f'<a class="download" href="{prefix}csv/{html.escape(csv_name)}" '
        f'download="{html.escape(csv_name)}">CSVをダウンロード</a>'
        '</div>'
    )

    parts.append(render_indicator_card(indicator_def, country["id"]))
    return f'<section class="indicator-block">{"".join(parts)}</section>'


# =============================================================
# ページ生成
# =============================================================

def render_top_page(indicators_global: list[dict], today: str) -> str:
    country_cards = []
    for c in COUNTRIES:
        country_cards.append(
            f'<a class="catalog-card" href="{c["id"]}/">'
            f'<div class="card-title">{html.escape(c["name_en"])} / {html.escape(c["name_ja"])}</div>'
            f'<div class="card-subtitle">国別ページへ</div>'
            f'</a>'
        )

    indicator_cards = []
    for ind in sorted(indicators_global, key=lambda x: x["display_order"]):
        slug = INDICATOR_URL_SLUG[ind["id"]]
        indicator_cards.append(
            f'<a class="catalog-card" href="indicator/{slug}/">'
            f'<div class="card-title">{html.escape(ind["label"])}</div>'
            f'<div class="card-subtitle">{html.escape(ind["id"])}</div>'
            f'</a>'
        )

    body = (
        '<header class="site-header">'
        '<h1>Crisis Frontier Global Data Monitor</h1>'
        '<p class="subtitle">国際金融の基礎統計を、観察するための港</p>'
        f'<p class="updated">更新日：{html.escape(today)}</p>'
        '</header>'
        '<main>'
        '<h2>国カタログ</h2>'
        f'<div class="catalog">{"".join(country_cards)}</div>'
        '<h2>指標カタログ</h2>'
        f'<div class="catalog">{"".join(indicator_cards)}</div>'
        '</main>'
        + render_site_footer(depth=0)
    )
    return render_layout(title="Crisis Frontier Global Data Monitor", body_html=body, depth=0)


def render_country_page(
    country: dict,
    indicators_global: list[dict],
    data_index: dict[tuple[str, str], dict],
    conn: sqlite3.Connection,
    today: str,
) -> str:
    breadcrumb = render_breadcrumb([
        ("トップ", "../index.html"),
        (f'{country["name_en"]} / {country["name_ja"]}', None),
    ])

    blocks = []
    for ind in sorted(indicators_global, key=lambda x: x["display_order"]):
        key = (country["id"], ind["id"])
        entry = data_index.get(key)
        rows = fetch_observations(conn, country["id"], ind["id"]) if entry else []
        # CSV はデータがある場合のみ書き出す（プレースホルダではボタンを出さないため）
        if entry and rows:
            write_csv(rows, country["id"], ind["id"])
        blocks.append(render_indicator_block(ind, country, entry, rows, depth=1, today=today))

    body = (
        '<header class="site-header">'
        f'<h1>{html.escape(country["name_en"])} / {html.escape(country["name_ja"])}</h1>'
        f'<p class="updated">更新日：{html.escape(today)}</p>'
        '</header>'
        f'{breadcrumb}'
        '<main>'
        '<h2>主要指標</h2>'
        + "".join(blocks)
        + '</main>'
        + render_site_footer(depth=1)
    )
    return render_layout(
        title=f'{country["name_en"]} / {country["name_ja"]}',
        body_html=body,
        depth=1,
    )


def render_indicator_cross_page(
    indicator_def: dict,
    data_index: dict[tuple[str, str], dict],
    conn: sqlite3.Connection,
    today: str,
) -> str:
    """指標横断ページ：3カ国スロットを常設し、データがなければプレースホルダ。"""
    breadcrumb = render_breadcrumb([
        ("トップ", "../../index.html"),
        ("指標", None),
        (indicator_def["label"], None),
    ])

    blocks = []
    # 横断ページでは「指標カード（三層解説）」をページ冒頭に1度だけ出す
    intro_card = render_indicator_card(indicator_def)

    for c in COUNTRIES:
        key = (c["id"], indicator_def["id"])
        entry = data_index.get(key)
        rows = fetch_observations(conn, c["id"], indicator_def["id"]) if entry else []
        if entry and rows:
            write_csv(rows, c["id"], indicator_def["id"])
        # 横断ページでは「国名」を見出しに、各国スロットを並べる
        block = render_country_slot_for_indicator(
            indicator_def=indicator_def,
            country=c,
            data_entry=entry,
            rows=rows,
            today=today,
        )
        blocks.append(block)

    body = (
        '<header class="site-header">'
        f'<h1>{html.escape(indicator_def["label"])}</h1>'
        f'<p class="subtitle">指標横断ページ — 全国分を縦に並べて比較</p>'
        f'<p class="updated">更新日：{html.escape(today)}</p>'
        '</header>'
        f'{breadcrumb}'
        '<main>'
        f'{intro_card}'
        '<h2>各国の状況</h2>'
        + "".join(blocks)
        + '</main>'
        + render_site_footer(depth=2)
    )
    return render_layout(title=indicator_def["label"], body_html=body, depth=2)


def render_country_slot_for_indicator(
    indicator_def: dict,
    country: dict,
    data_entry: dict | None,
    rows: list[tuple[str, float | None]],
    today: str,
) -> str:
    """指標横断ページ用の国スロット（国別ページへの戻りリンク付き）。"""
    parts = []
    parts.append(
        f'<h3>{html.escape(country["name_en"])} / {html.escape(country["name_ja"])} '
        f'<span class="meta">'
        f'（<a href="../../{country["id"]}/">{html.escape(country["name_ja"])}ページへ</a>）'
        f'</span></h3>'
    )

    if data_entry is None:
        if country["id"] == "us" and indicator_def["id"] == "fx_usd":
            parts.append(
                f'<div class="placeholder not-applicable">'
                f'{html.escape(US_FX_USD_NOT_APPLICABLE)}'
                f'</div>'
            )
        else:
            parts.append(
                '<div class="placeholder">'
                f'この指標（{html.escape(country["name_ja"])} / {html.escape(indicator_def["label"])}）'
                'は今後収集予定です。'
                '</div>'
            )
        return f'<section class="indicator-block">{"".join(parts)}</section>'

    series_id = data_entry["series_id"]
    source_label = SOURCE_LABELS.get(data_entry.get("source", "fred"), data_entry.get("source", ""))
    frequency = data_entry.get("frequency", "")
    meta_text = (
        f'出典: {html.escape(source_label)} ({html.escape(series_id)}) ／ '
        f'頻度: {html.escape(frequency)} ／ '
        f'更新日: {html.escape(today)}'
    )
    parts.append(f'<p class="meta">{meta_text}</p>')

    img_name = f"{country['id']}_{indicator_def['id']}.png"
    img_path = IMG_DIR / img_name
    if img_path.exists():
        parts.append(
            f'<img class="chart" src="../../images/{html.escape(img_name)}" '
            f'alt="{html.escape(country["name_ja"])} {html.escape(indicator_def["label"])}">'
        )
    else:
        parts.append(f'<p class="no-data">画像未生成: {html.escape(img_name)}</p>')

    summary = compute_summary(rows)
    if summary is not None:
        parts.append(render_summary_table(summary))
    else:
        parts.append('<p class="no-data">観測値がありません</p>')

    csv_name = f"{country['id']}_{indicator_def['id']}.csv"
    parts.append(
        '<div class="actions">'
        f'<a class="download" href="../../csv/{html.escape(csv_name)}" '
        f'download="{html.escape(csv_name)}">CSVをダウンロード</a>'
        '</div>'
    )
    return f'<section class="indicator-block">{"".join(parts)}</section>'


def render_data_paths_page(data_sources: list[dict], today: str) -> str:
    """再配信経路（FRED, World Bank 等）の説明ページ。"""
    breadcrumb = render_breadcrumb([
        ("トップ", "../index.html"),
        ("データ取得経路", None),
    ])

    # 系列一覧表
    rows_html = []
    for e in data_sources:
        rows_html.append(
            '<tr>'
            f'<td>{html.escape(e["country_id"])}</td>'
            f'<td>{html.escape(e["indicator_id"])}</td>'
            f'<td>{html.escape(SOURCE_LABELS.get(e.get("source", ""), e.get("source", "")))}</td>'
            f'<td>{html.escape(e.get("series_id", ""))}</td>'
            f'<td>{html.escape(e.get("frequency", ""))}</td>'
            '</tr>'
        )
    table_html = (
        '<table class="paths">'
        '<thead><tr>'
        '<th>country_id</th><th>indicator_id</th><th>再配信元</th>'
        '<th>系列ID</th><th>頻度</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
    )

    body = (
        '<header class="site-header">'
        '<h1>データ取得経路</h1>'
        '<p class="subtitle">本サイトが利用する再配信経路の説明</p>'
        f'<p class="updated">更新日：{html.escape(today)}</p>'
        '</header>'
        f'{breadcrumb}'
        '<main>'

        '<h2>本ページの位置づけ</h2>'
        '<p>各指標の <em>source_note</em> には、データの一次源（中央銀行・財務省・統計局など）のみを記載しています。'
        '本サイトが実際に取得経路として利用している再配信元（FRED、World Bank、IMF SDMX、OECD SDMX、BIS SDMX）の説明は、本ページに集約します。'
        '一次源と再配信元の役割を分けることで、データの権威性と取得経路の利便性を切り分けて理解できるようにする趣旨です。</p>'

        '<h2>FRED（Federal Reserve Economic Data）</h2>'
        '<p>FRED は米国セントルイス連邦準備銀行（Federal Reserve Bank of St. Louis）が運営する経済データベースです。'
        '世界各国の中央銀行・統計局が公表する系列を集約し、機械可読な API を提供しています。'
        '本サイトでは、為替レート（DEXJPUS, DEXTHUS）、米国実効連邦資金金利（DFF）、'
        '日本の短期金利系列（IRSTCI01JPM156N）などを FRED 経由で取得しています。'
        'FRED 自体は一次源ではなく、各系列の発行元はそれぞれの中央銀行・統計局です。'
        '利用には API キーが必要で、無償で発行されます。</p>'

        '<h2>World Bank Data API</h2>'
        '<p>World Bank Data API は、世界銀行が提供するオープンな統計 API です。'
        '世界銀行が各国から収集・編纂した世界開発指標（World Development Indicators, WDI）などが含まれます。'
        '本サイトでは、タイの外貨準備高（FI.RES.TOTL.CD：金を含む年次値、米ドル建て）の取得に利用しています。'
        'World Bank も中継機関であり、原データは各国中央銀行が提出した値です。</p>'

        '<h2>IMF SDMX（国際通貨基金 統計データ）</h2>'
        '<p>IMF SDMX は、国際通貨基金（IMF）統計局が提供する SDMX 2.1 規格の API です。'
        '本サイトでは、タイの政策金利（MFS_IR：公定歩合）、日本・タイの中央銀行総資産（MFS_CBS：S121_A_TA_ASEC_CB1SR）、'
        'タイの10年国債利回り（MFS_IR：S13BOND_RT_PT_A_PT）を取得しています。'
        '旧来の「IFS」という単一データセットは存在せず、現在はトピック別の193データフロー'
        '（CPI、MFS_IR、MFS_CBS、IRFCL など）に分割されています。国コードは alpha-3（JPN、THA）を使用します。</p>'

        '<h2>OECD SDMX（経済協力開発機構 統計データ）</h2>'
        '<p>OECD SDMX は、OECD 統計局が提供する SDMX 2.1 規格の API（SDMX-JSON 形式）です。'
        '本サイトでは、日本の消費者物価指数（DSD_PRICES_COICOP2018：COICOP 2018 分類、月次、Index 2015=100）を取得しています。'
        '主に OECD 加盟国の系列を集約しており、タイは加盟国でないため OECD 経由では取得していません。</p>'

        '<h2>BIS SDMX（国際決済銀行 統計データ）</h2>'
        '<p>BIS SDMX は、国際決済銀行（BIS）が各国中央銀行と共同で編纂する長期統計の API（SDMX 2.1 XML 形式）です。'
        '本サイトでは、タイの消費者物価指数（WS_LONG_CPI：月次、Index 2010=100、UNIT_MEASURE=628）を取得しています。'
        'BIS の長期 CPI 系列はタイを 1976 年以降カバーしており、1997 年アジア通貨危機期の物価動向を月次粒度で観察できる'
        '点が特徴です。国コードは alpha-2（JP、TH）を使用するため IMF / OECD と異なります。</p>'

        '<h2>頻度の読み方</h2>'
        '<p>各系列の更新頻度は、指標カードのメタ行と下表「頻度」列に明記しています。読み方の目安は次のとおりです。</p>'
        '<ul>'
        '<li><strong>日次</strong>：営業日ごとに値が更新される。為替レートや短期金利など、市場で連続的に値が付くものに多い。短期の急変を捉えやすい一方、ノイズも大きい。</li>'
        '<li><strong>週次</strong>：1週ごとに1点。中央銀行のバランスシート報告（米国FRBのH.4.1など）でよく用いられる。日次よりは粗いが、月次よりは速い動きを捉えられる。</li>'
        '<li><strong>月次</strong>：暦月ごとに1点。CPI、政策金利の月平均値、月末ストック値などが該当する。月内の動きは観察できないが、傾向の把握には十分な粒度。</li>'
        '<li><strong>四半期</strong>：3か月ごとに1点。GDP や国際収支などマクロ集計値に多い。粒度は粗いが、構造的な変化を捉えやすい。</li>'
        '<li><strong>年次</strong>：1年ごとに1点。世界銀行系列など、国際比較を意識した編纂値に多い。長期トレンドの観察に適するが、年内の局面変化は見えない。</li>'
        '</ul>'
        '<p>頻度が異なる系列を同じグラフで重ねると誤読を招くため、本サイトでは各指標カードの単位で表示し、頻度を明示しています。</p>'

        '<h2>本サイトが利用している系列の一覧</h2>'
        f'{table_html}'

        '<h2>将来追加予定の経路</h2>'
        '<p>以下は国別参考指標（indicators_country_specific）の整備に伴い追加が検討される経路です。'
        '本フェーズには含めず、ニーズが具体化した時点で実装します。</p>'
        '<ul>'
        '<li>e-Stat（日本：総務省統計局）：日本固有の系列（生鮮食品を除くコアCPI、所得階層別 CPI など）の取得。'
        '利用には appId（無償）の事前登録が必要。</li>'
        '<li>TPSO（タイ：商務省貿易政策戦略局, index-api.tpso.go.th）：タイ固有の系列'
        '（一般／低所得／非都市部の所得階層別 CPI、地方別 CPIP など）の取得。利用には API キーの事前照会が必要。</li>'
        '</ul>'

        '</main>'
        + render_site_footer(depth=1)
    )
    return render_layout(title="データ取得経路", body_html=body, depth=1)


# =============================================================
# main
# =============================================================

def main() -> int:
    config = load_config()
    indicators_global = config["indicators_global"]
    data_sources = config["data_sources"]
    data_index = index_data_sources(data_sources)

    if not DB_PATH.exists():
        print(f"DBが見つかりません: {DB_PATH}", file=sys.stderr)
        return 1

    today = datetime.now().strftime("%Y-%m-%d")

    HTML_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        # ---- トップページ
        top_html = render_top_page(indicators_global, today)
        (HTML_DIR / "index.html").write_text(top_html, encoding="utf-8")
        print(f"HTML生成: {HTML_DIR / 'index.html'}")

        # ---- 国別ページ
        for c in COUNTRIES:
            country_dir = HTML_DIR / c["id"]
            country_dir.mkdir(parents=True, exist_ok=True)
            doc = render_country_page(c, indicators_global, data_index, conn, today)
            (country_dir / "index.html").write_text(doc, encoding="utf-8")
            print(f"HTML生成: {country_dir / 'index.html'}")

        # ---- 指標横断ページ
        indicator_root = HTML_DIR / "indicator"
        indicator_root.mkdir(parents=True, exist_ok=True)
        for ind in indicators_global:
            slug = INDICATOR_URL_SLUG[ind["id"]]
            ind_dir = indicator_root / slug
            ind_dir.mkdir(parents=True, exist_ok=True)
            doc = render_indicator_cross_page(ind, data_index, conn, today)
            (ind_dir / "index.html").write_text(doc, encoding="utf-8")
            print(f"HTML生成: {ind_dir / 'index.html'}")

        # ---- データ取得経路ページ
        paths_dir = HTML_DIR / "data-paths"
        paths_dir.mkdir(parents=True, exist_ok=True)
        doc = render_data_paths_page(data_sources, today)
        (paths_dir / "index.html").write_text(doc, encoding="utf-8")
        print(f"HTML生成: {paths_dir / 'index.html'}")

    finally:
        conn.close()

    print(f"CSV出力先: {CSV_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
