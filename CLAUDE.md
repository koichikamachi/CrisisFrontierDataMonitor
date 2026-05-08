CLAUDE.md



\# Crisis Frontier Global Data Monitor



\## プロジェクト概要

主要国の基礎経済・国際金融統計を日次取得し、

静的HTML/PNGで可視化する研究・教育向けデータ基盤。

BKW研究所（bookkeepingwhisperer.org）の公開プロジェクト。



\## 開発フェーズ

現在：フェーズ1の最初の一歩（2カ国×2指標の最小動作確認）

次段階：国と指標の順次追加



\## 仕様の正本

\- 全体仕様：docs/SPEC.docx

\- 指標とFRED系列コードの対応：docs/SPEC.docx の6.3節

\- APIキーの扱い：docs/SPEC.docx の6.4節



\## 開発方針

\- 幹を一本通すことを最優先

\- 2カ国×2指標の現実のコードを直接書く（過剰な抽象化を避ける）

\- 責務分離：取得・整形・描画・HTML出力は別スクリプト

\- パスはすべて相対指定（Path(\_\_file\_\_).resolve().parent 基準）

\- .env に認証情報、.gitignore で除外

\- コメントは日本語で簡潔に

\- 作らないもの：plotly、chart.js、WordPress連携、AI解説、

&#x20; cron自動化、Docker（いずれも後続フェーズで追加）



\## 技術スタック

\- Python 3.10（Windows 11）

\- ライブラリ：fredapi, pandas, matplotlib, python-dotenv

\- データベース：SQLite

\- 出力：PNG（matplotlib）とHTML



\## ディレクトリ構成

CrisisFrontierDataMonitor/

├─ scripts/      # fetch\_data.py, build\_charts.py, export\_html.py

├─ config/       # indicators.yaml

├─ data/         # crisis\_frontier.db（.gitignoreで除外）

├─ outputs/      # images/, html/（いずれも.gitignoreで除外）

├─ logs/         # run.log（.gitignoreで除外）

├─ docs/         # SPEC.docx

├─ .env          # APIキー（.gitignoreで除外）

├─ .env.example

├─ .gitignore

├─ requirements.txt

├─ README.md

└─ run\_all.py



\## GitHub

\- Owner: koichikamachi

\- Repository: CrisisFrontierDataMonitor

\- Visibility: Private



\## 用語

\- BKW：Bookkeeping Whisperer Institute（BKW研究所）

\- Crisis Frontier：危機兆候を観測する研究の総称


## フェーズ2の構造方針（港の構造）

### indicators.yaml の構造

indicators.yaml は次の三層に分ける。

- `indicators_global`: 全国共通のコア指標定義（id, label, display_order, description, source_note, how_to_read）
- `indicators_country_specific`: 国別参考指標。フェーズ4以降で各国セクションを追加。本フェーズでは空辞書 `{}` を維持。
- `data_sources`: country_id × indicator_id × source × series_id の割当表

`indicators_country_specific` が空であっても、サンプルデータの投入や補完提案は不要。空のまま維持する。

### 命名規約

- indicator_id, country_id ともに小文字スネークケース
- URL では indicator_id のアンダースコアをハイフンに変換（`fx_usd` → `/indicator/fx-usd/`）
- ファイル名は `country_id_indicator_id.png` 形式を維持（既存どおり）

### コア6指標と固定順序

国別ページにおける指標表示順は次のとおり、必ず固定。

1. `fx_usd`
2. `policy_rate`
3. `bond_10y`
4. `cpi`
5. `fx_reserves`
6. `central_bank_total_assets`

### URL 設計

- 国別: `/{country_id}/`（例: `/jp/`）
- 指標別: `/indicator/{indicator-id-hyphen}/`
- データ取得経路: `/data-paths/`
- トップ: `/index.html`

### source_note の方針

`source_note` には一次源（中央銀行・財務省・統計局など）のみを記載する。FRED や World Bank などの再配信経路は書かない。再配信経路は `/data-paths/` ページで一括説明する。

### Step 4（仮公開）と Step 7（自動運航）

- 仮公開先は GitHub Pages または Cloudflare Pages を予定
- 自動運航は GitHub Actions による（cron は採用しない）
- 本フェーズには含めない。フェーズ3で別途実装する。

