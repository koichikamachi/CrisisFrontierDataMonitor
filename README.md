# Crisis Frontier Global Data Monitor

主要国の基礎経済・国際金融統計を日次取得し、静的HTML/PNGで可視化する研究・教育向けデータ基盤。
BKW研究所（[bookkeepingwhisperer.org](https://bookkeepingwhisperer.org)）の公開プロジェクトの一部。

## 目的

国際金融を学ぶ学生・若手研究者のために、主要国の基礎経済・金融統計を日次で取得し、
時系列グラフで可視化する公開データ基盤を提供します。

## 現在の実装範囲（フェーズ1の最初の一歩）

幹を一本通すことを優先した最小動作確認版。

- 対象国：日本、米国
- 対象指標：対米ドル為替レート、政策金利
- データソース：FRED（Federal Reserve Economic Data）
- 取得期間：1990年1月1日以降
- 取得系列（米国の対米ドル為替は定義上存在しないため計3系列）：
  - 日本×為替： `DEXJPUS`（円/ドル、日次）
  - 米国×政策金利： `DFF`（Federal Funds Effective Rate、日次）
  - 日本×政策金利： `IRSTCI01JPM156N`（コール市場金利、月次）
- 出力：matplotlibによる静的PNGとそれを埋め込んだ静的HTML
- 保存：SQLite

## 一次実装には含まないもの（二次段階以降で追加）

- 他の国・他の指標
- plotly / chart.js 等のインタラクティブ描画
- WordPress連携
- AI解説文生成
- cron / タスクスケジューラによる自動実行
- Docker化

## ディレクトリ構成

```
CrisisFrontierDataMonitor/
├─ scripts/
│   ├─ fetch_data.py       # FREDから取得しSQLiteに保存
│   ├─ build_charts.py     # SQLiteからPNG生成
│   └─ export_html.py      # 静的HTML出力
├─ config/
│   └─ indicators.yaml     # 国・指標・FRED系列の対応
├─ data/                   # crisis_frontier.db（.gitignoreで除外）
├─ outputs/
│   ├─ images/             # PNG出力先
│   └─ html/               # HTML出力先
├─ logs/                   # run.log（.gitignoreで除外）
├─ docs/                   # SPEC
├─ .env.example
├─ .gitignore
├─ requirements.txt
├─ README.md
└─ run_all.py
```

## セットアップ手順（Windows 11 / PowerShell）

### 1. 仮想環境の作成と有効化

```powershell
cd C:\Users\MyProjectsOnWin\CrisisFrontierDataMonitor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 依存ライブラリのインストール

```powershell
pip install -r requirements.txt
```

### 3. FRED APIキーの取得

1. [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) にアクセス
2. アカウント作成（無料）後、My Account → API Keys からキーを発行
3. 32桁の英数字のキーが発行される

### 4. .env ファイルの作成

`.env.example` をコピーして `.env` を作成し、取得したAPIキーを書き込みます。

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` の内容：
```
FRED_API_KEY=取得した32桁のキー
```

`.env` は `.gitignore` で除外されているためGitには含まれません。

## 実行手順

```powershell
python run_all.py
```

3つのスクリプトが順に実行されます：
1. `fetch_data.py` … FREDから3系列を取得してSQLiteへ保存
2. `build_charts.py` … SQLiteからPNGを3枚生成
3. `export_html.py` … `outputs/html/index.html` を生成

各段階の成否とエラーは `logs/run.log` に追記されます。
1つの系列の取得が失敗しても全体は停止せず、可能な範囲で出力を生成します。

## 出力の場所

- グラフ画像： `outputs/images/{country_id}_{indicator_id}.png` （例: `JP_fx_usd.png`）
- HTML： `outputs/html/index.html` （ブラウザで開いて閲覧）

## 二次実装予告

フェーズ1の続きとして、以下を順次追加予定：

- 主要先進国（英、独、仏、加、豪、スイス、NZ）の追加
- 主要新興国（中、韓、印、ブラジル、メキシコ、トルコ、南ア、タイ）の追加
- 指標の拡充：消費者物価指数、長短金利差、株価指数、外貨準備、貿易収支等
- summaries テーブルおよび要約テキスト
- WordPress連携、AI解説、自動実行（cron / Task Scheduler）

## GitHub リポジトリ作成手順

このリポジトリは Private を想定しています（Owner: `koichikamachi`）。

### `gh` コマンドが使える場合

```powershell
git init -b main
git add .
git commit -m "chore: initial scaffold for phase 1 minimum"
gh repo create koichikamachi/CrisisFrontierDataMonitor --private --source=. --push
```

### `gh` コマンドが無い場合

1. GitHub Web で空の Private リポジトリ `koichikamachi/CrisisFrontierDataMonitor` を作成（README/`.gitignore`はチェックしない）
2. ローカルで以下を実行：

```powershell
git init -b main
git add .
git commit -m "chore: initial scaffold for phase 1 minimum"
git remote add origin https://github.com/koichikamachi/CrisisFrontierDataMonitor.git
git push -u origin main
```

## 仕様の正本

- 全体仕様：`docs/SPEC.docx`
- 指標とFRED系列コードの対応：仕様書6.3節
- データモデル：仕様書16節
