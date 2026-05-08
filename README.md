# Crisis Frontier Global Data Monitor

主要国の基礎経済・国際金融統計を日次取得し、静的HTML/PNGで可視化する研究・教育向けデータ基盤である。BKW研究所（[bookkeepingwhisperer.org](https://bookkeepingwhisperer.org)）が運営する公開研究プロジェクトの一部。

## このサイトの位置づけ

国際金融を学ぶ学生・若手研究者にとって、各国の主要な経済・金融統計を一望できる場所は、思いのほか少ない。各国の中央銀行、財務省、統計局がそれぞれ独自のフォーマットでデータを公表しており、横断的に比較するには相応の手間がかかる。本プロジェクトは、その入口を整える試みである。

本プロジェクトはまた、BKW研究所が進める Crisis Frontier（危機境界）研究の素材基盤としても機能する。Crisis Frontier 研究は、通貨危機を金融システムの状態空間における境界問題として再定式化する試みであり、本データ基盤は、その動学的研究のための観測装置という側面を併せ持つ。

これら二つの目的、すなわち「教育のための基礎データの公開拠点」と「研究のための観測インフラ」は、互いに補強しあう関係にある。

## 現在の実装範囲（フェーズ2完了時点）

「港の構造」を確立するフェーズが完了した状態にある。船（国・指標）はあとから順次増やすが、港の構造（情報設計・ナビゲーション・URL規約）は固定済みである。

### 対象国

日本（jp）、米国（us）、タイ（th）の3か国。

### 6コア指標枠

すべての国別ページにおいて、次の順序で固定表示する。

1. 為替レート（対米ドル）
2. 政策金利
3. 10年国債利回り
4. 消費者物価指数（CPI）
5. 外貨準備
6. 中央銀行総資産

各指標カードは、description（これは何か）、source_note（誰が出しているか）、how_to_read（どう読むか）の三層解説を備える。学部生にも研究者にも届く粒度として設計した。

### 稼働中のデータ系列

現在、次の5系列が稼働している。残りの指標枠は「収集予定」のプレースホルダとして枠だけ確保してある。

| 国 | 指標 | データソース | 系列ID | 頻度 |
|---|---|---|---|---|
| 日本 | 為替レート | FRED | DEXJPUS | 日次 |
| 日本 | 政策金利 | FRED | IRSTCI01JPM156N | 月次 |
| 米国 | 政策金利 | FRED | DFF | 日次 |
| タイ | 為替レート | FRED | DEXTHUS | 日次 |
| タイ | 外貨準備 | World Bank | FI.RES.TOTL.CD | 年次 |

### サイト構造

訪問者から見えるページ群は次のとおり。

- トップページ（国カタログと指標カタログ）
- 国別ページ（3ページ）
- 指標横断ページ（6ページ、国際比較用）
- データ取得経路ページ（再配信経路の説明）

すべてのページから、トップとデータ取得経路に戻る導線を備える。

## セットアップ手順（Windows 11 / PowerShell）

### 1. 仮想環境の作成と有効化

```powershell
cd C:\path\to\CrisisFrontierDataMonitor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 依存ライブラリのインストール

```powershell
pip install -r requirements.txt
```

### 3. FRED API キーの取得

[https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) でアカウントを作成（無料）し、My Account → API Keys からキーを発行する。32桁の英数字のキーが発行される。

### 4. .env ファイルの作成

`.env.example` をコピーして `.env` を作成し、取得した API キーを書き込む。

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` の内容は次のとおり。

```
FRED_API_KEY=取得した32桁のキー
```

`.env` は `.gitignore` で除外されているため Git には含まれない。

## 実行手順

```powershell
python run_all.py
```

4つのスクリプトが順に実行される。

1. `fetch_data.py`: FRED から系列を取得して SQLite へ保存
2. `fetch_worldbank.py`: World Bank Data API から系列を取得
3. `build_charts.py`: SQLite から PNG グラフを生成
4. `export_html.py`: 国別・指標別の静的 HTML サイトを生成

各段階の成否は `logs/run.log` に追記される。1つの系列の取得が失敗しても全体は停止せず、可能な範囲で出力を生成する設計とした。

## ローカルでの閲覧

ブラウザでファイルを直接開くと、URLの末尾スラッシュ問題でナビゲーションが意図どおりに動作しない場合がある。代わりに簡易 HTTP サーバーを立てて閲覧することを推奨する。

```powershell
python -m http.server 8000 --directory outputs/html
```

ブラウザで `http://localhost:8000/` を開けば、本番公開時と同じ挙動でサイトを確認できる。

## ディレクトリ構成

```
CrisisFrontierDataMonitor/
├── scripts/
│   ├── fetch_data.py
│   ├── fetch_worldbank.py
│   ├── build_charts.py
│   └── export_html.py
├── config/
│   └── indicators.yaml      # 三層構造（global / country_specific / data_sources）
├── data/                     # SQLite データベース（.gitignore で除外）
├── outputs/
│   └── html/
│       ├── css/site.css
│       ├── images/           # PNG 出力先（.gitignore で除外）
│       ├── csv/              # CSV ダウンロード用（.gitignore で除外）
│       ├── jp/, us/, th/     # 国別ページ
│       ├── indicator/        # 指標横断ページ
│       └── data-paths/       # データ取得経路ページ
├── logs/                     # 実行ログ（.gitignore で除外）
├── docs/                     # 補助文書
├── .env.example
├── .gitignore
├── requirements.txt
├── run_all.py
├── README.md
├── CLAUDE.md
└── LICENSE
```

## 設計思想

### 港のメタファ

本プロジェクトの設計判断は、「港を造る」というメタファに沿って進めてきた。船（国・指標）はあとからいくらでも増やせるが、港の構造（情報設計・ナビゲーション・URL規約）は最初に決めなければならない。フェーズ2では、岸壁と航路と水先案内人にあたるものを揃えることを優先した。

### 観測マニュアル原則

各指標の解説は、辞書ではなく観測マニュアルとして書く。description は中立的に短く、source_note は一次源（中央銀行・財務省・統計局など）のみを記載し、再配信経路（FRED、World Bank 等）は別ページで一括説明する。how_to_read のみ、わずかに行為指示を含む。三層分離は、訪問者の読みの呼吸に合わせて設計した。

### 二層構造の指標定義

`config/indicators.yaml` は次の三層に分かれている。

- `indicators_global`: 全国共通のコア指標定義
- `indicators_country_specific`: 国別参考指標（フェーズ4以降で各国セクションを追加。現時点では空辞書を維持）
- `data_sources`: 国×指標×データソースの割当表

指標定義（普遍）とデータソース割当（個別）が独立しているため、新しい国を追加するときも、`data_sources` への追記だけで済むよう設計した。

## 今後の予定

### フェーズ3：港を世に開く

- 仮公開（GitHub Pages または Cloudflare Pages）
- GitHub Actions による日次自動更新

### フェーズ4：船を増やす

1997年アジア通貨危機の文脈にあわせ、マレーシア、インドネシア、韓国を順次追加。`bond_10y`、`cpi`、`central_bank_total_assets` の系列もあわせて拡充する。

### フェーズ5：研究と教育の二重性の顕在化

BIS、IMF、OECD など追加データソースの統合。`indicators_country_specific` の本格運用（タイの信用GDP乖離率、短期対外債務、不良債権比率等）。これらは Crisis Frontier 研究の状態変数候補として、研究本体との接続点となる。

## 引用について

学術的な参照には、次の形式を推奨する。

```
蒲池孝一 (2026) 『Crisis Frontier Global Data Monitor』 BKW研究所
https://github.com/koichikamachi/CrisisFrontierDataMonitor
```

## ライセンス

本プロジェクトは MIT License の下で公開する。詳細は [LICENSE](LICENSE) を参照。

## 連絡先

BKW研究所

- ウェブサイト: [bookkeepingwhisperer.org](https://bookkeepingwhisperer.org)
- リポジトリ: [github.com/koichikamachi/CrisisFrontierDataMonitor](https://github.com/koichikamachi/CrisisFrontierDataMonitor)
