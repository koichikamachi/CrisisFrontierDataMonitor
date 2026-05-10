# データソース調査報告書 — 未取得12枠の系列特定

> **2026-05-10 注記**: 2026-05-10のローカル検証で前提変更が判明。最新は [`data_source_verification_2026-05.md`](data_source_verification_2026-05.md) を参照。

- **作成日**: 2026-05-09
- **対象**: フェーズ2.5（仮称）
- **目的**: 未取得12枠（jp/us/th 各4枠）について、データ取得経路と系列IDを特定する
- **報告書スコープ**: 系列の存在確認のみ。yaml 更新・コード変更・データ取得は本作業に含めない

---

## 0. 調査前提（蒲池さんとの合意事項）

| 論点 | 採用方針 |
|---|---|
| FRED の粒度（日次／月次の混在） | 取れる最高粒度を採用。`frequency` フィールドで明示。3カ国の見え方は見出し・順序・カードのフォーマットで揃える |
| タイの1997年連続性 | 「1997前後カバー最良経路」と「1990年以降完全連続経路」が乖離する場合は両方併記し、最終判断は蒲池さんに委ねる |
| 中央銀行総資産の定義 | 厳密に Total Assets（**資産側合計**）を優先。マネタリーベース（負債側集計）は概念的に異なる別系列であり、代替ではない旨を特記事項に明示 |

---

## 1. 調査結果の検証ステータス（重要）

本調査は4つの並列リサーチエージェントを使って実施した。**いずれのエージェントも実行サンドボックス内で外部Web/API（FRED, BIS, BOJ, BOT等）への直接アクセスが拒否された**ため、以下の系列ID・開始日・単位等は、各系列の確立されたメタ情報（FRED系列ページ・OECD MEI/IMF IFS再配信慣行・BOT/BOJ公式ドキュメント）に基づく回答である。

yaml 反映前に、本プロジェクトの通常環境から以下のスニペットでローカル検証することを推奨する（**本作業には含まない**）：

```python
from fredapi import Fred
from os import environ
f = Fred(api_key=environ["FRED_API_KEY"])
for sid in [
    "DGS10", "IRLTLT01JPM156N", "INTGSBTHM193N", "IRLTLT01THM156N",
    "CPIAUCNS", "JPNCPIALLMINMEI", "THACPIALLMINMEI",
    "WALCL", "TRESEGJPM052N", "TRESEGUSM052N", "INTDSRTHM193N",
]:
    info = f.get_series_info(sid)
    print(sid, "|", info["observation_start"], "→", info["observation_end"],
          "|", info["frequency"], "|", info["units"])
```

`THACPIALLMINMEI` が 404 する場合は `CPALTT01THM661N` にフォールバック。

---

## 2. 12枠の系列対応表

凡例：難易度 ☆=容易（FRED API一発）／☆☆=中（系列合成・新規フェッチャ要）／☆☆☆=難（独自API・手動取得）

### 2.1 日本（jp）4枠

| 国 | 指標 | 一次源 | 推奨経路 | 系列ID | 期間 | 頻度 | 単位 | 難易度 |
|---|---|---|---|---|---|---|---|---|
| jp | bond_10y | 財務省・日本銀行 | FRED（OECD MEI再配信） | `IRLTLT01JPM156N` | 1989-09 → 現在 | 月次 | % p.a., NSA | ☆ |
| jp | cpi | 総務省統計局 | FRED（OECD MEI再配信） | `JPNCPIALLMINMEI` | 1960-01 → 現在 | 月次 | 指数（2015=100, NSA） | ☆ |
| jp | fx_reserves | 財務省（外貨準備等の状況） | FRED（IMF IFS再配信） | `TRESEGJPM052N` | 1957-01 → 現在 | 月次 | USD（百万ドル想定）、NSA、ex-gold | ☆ |
| jp | central_bank_total_assets | 日本銀行（営業旬報） | **BOJ stat-search 直接** | `MD02'MABJ_MABJAA` 系統「資産合計」 | 1998 → 現在（機械可読） | 旬次（10日ごと）／月次平均 | JPY 100M（億円） | ☆☆☆ |

**特記事項（jp）**

- `bond_10y` の `IRLTLT01JPM156N` は OECD MEI が財務省 JGB 10年ベンチマーク利回りの月平均を再配信したもの。日次が必要なら財務省直接 CSV（`mof.go.jp/english/policy/jgbs/...`）が一次源だが、独自フェッチャが必要となるため難易度☆☆☆相当。本フェーズでは月次で十分。
- `cpi` は日本国内では5年ごと（…2010, 2015, 2020 base）に基準改定があるが、OECD MEI 配信はこれを内部チェインして 2015=100 の連続系列として配信している。スプライス処理は不要。「総合（all items）」で生鮮食品・エネルギーも含む。
- `fx_reserves` の IMF IFS 定義は **金を除く** 外貨準備（ex-gold）。財務省が一般に発表する「外貨準備等の状況」は金・SDR・IMFリザーブポジションを含むため、IFS 系列とは水準がやや異なる。`/data-paths/` で「金を除く定義を採用」と明示すれば足りる。
- `central_bank_total_assets` は本枠で**最大の難所**。**FREDには日銀の資産側Total Assets系列は存在しない**。FREDで取れるのはマネタリーベース（`MYAGM*JPM189N` 系列、`MABMM301JPM189S` 等）だが、これらは**負債側集計**であり、資産側Total Assetsの代替にはならない（蒲池さんの指摘どおり、概念的に別物）。
  - 推奨：BOJ 時系列統計データ検索（`stat-search.boj.or.jp`）から「営業毎旬報告（資産・負債）」の資産合計行を CSV ダウンロードする独自フェッチャを実装。1998年以降が機械可読。1990年代前半は紙ベースの歴史アーカイブを手動投入する必要がある。
  - 代替：IMF IFS SDMX 経由の「Central Bank: Total Assets」（タイと同じ経路）。新規 SDMX クライアントが必要だが、3カ国で経路を統一できる利点あり。

### 2.2 米国（us）4枠

| 国 | 指標 | 一次源 | 推奨経路 | 系列ID | 期間 | 頻度 | 単位 | 難易度 |
|---|---|---|---|---|---|---|---|---|
| us | bond_10y | 米国財務省（Treasury Constant Maturity, FRB H.15） | FRED | `DGS10` | 1962-01-02 → 現在 | 日次（営業日） | %、NSA | ☆ |
| us | cpi | 労働統計局（BLS） | FRED | `CPIAUCNS`（NSA） | 1947-01 → 現在 | 月次 | 指数（1982-84=100, NSA） | ☆ |
| us | fx_reserves | 財務省・連邦準備制度（U.S. International Reserve Position） | FRED（IMF IFS再配信） | `TRESEGUSM052N` | 1957-01 → 現在（要確認） | 月次 | USD（百万ドル想定）、NSA、ex-gold | ☆ |
| us | central_bank_total_assets | 連邦準備制度（H.4.1） | FRED | `WALCL` | **2002-12-18** → 現在 | 週次（水曜日） | USD 百万ドル、NSA | ☆ |

**特記事項（us）**

- `bond_10y` の `DGS10` は祝日・入札不調日に "Not Available" となり `fredapi` で `NaN` を返す。`dropna()` で対応可能。月平均が欲しければ `GS10`（同じデータの月次平均）。
- `cpi` は **NSA（`CPIAUCNS`）を採用** することで、日本（`JPNCPIALLMINMEI` は NSA）・タイ（OECD MEI 配信は NSA）と方法論を揃える。SA系列（`CPIAUCSL`）は YoY 変化率で見れば同じだが、3カ国比較で混在させると視覚的不整合が出る。
- 基準年は米国が 1982-84=100、日本・タイが 2015=100 で異なる。指数水準を直接並べるのではなく、**YoY%（前年同月比）で表示** することでこの差を吸収できる（描画段階の判断、本フェーズの設計事項としては記録のみ）。
- `fx_reserves` について：**米国は国際基軸通貨の発行国であり、外貨準備（ex-gold で USD 35〜40bn 程度）はGDP比で極めて小さい**。日本・タイの危機指標としての意味と異なり、米国においてはほぼフラットで「危機シグナル」性は乏しい。3カ国パネルの対称性のために掲載するが、`how_to_read` では「米国の場合は構造的指標であり、ドル体系のストレス指標としては FRB の USD スワップライン残高（FRED `SWPT`）を別途参照することが望ましい」旨を記すと読者に親切。
- `central_bank_total_assets` の `WALCL` は **2002-12-18 開始** で、1990〜2002年の連続系列はFRED上に存在しない。
  - 蒲池さんへの判断材料：(a) 2002年開始のまま採用しチャートに注記する、(b) FRB の H.4.1 アーカイブから手動で 1990年代を継ぎ足す、(c) 本指標について米国は「2002年以降」とする方針を全体に適用する、のいずれかを選ぶ必要がある。本プロジェクトの主眼が1997年危機よりも構造的観察にあるなら (a) で十分。
  - **これは資産側Total Assetsであり、マネタリーベース（`BOGMBASE`, `AMBNS`, `BASE`）や流通通貨（`CURRCIR`）とは別物**。後者を代替に使ってはならない。

### 2.3 タイ（th）4枠

| 国 | 指標 | 一次源 | 推奨経路 | 系列ID | 期間 | 頻度 | 単位 | 難易度 |
|---|---|---|---|---|---|---|---|---|
| th | policy_rate（経路A／1990年以降連続） | Bank of Thailand（Bank Rate） | FRED（IMF IFS再配信） | `INTDSRTHM193N` | ~1970年代 → 現在（要確認） | 月次 | % p.a. | ☆ |
| th | policy_rate（経路B／現行レジーム厳密） | Bank of Thailand（1日物RP） | BIS `cbpol` または BOT直接 | （BIS cbpol → TH） | 14日RP: 2000-05-23-／1日RP: 2007-01-17- | 日次（BIS） | % p.a. | ☆☆〜☆☆☆ |
| th | bond_10y（経路A／1997カバー） | Bank of Thailand | FRED（IMF IFS再配信） | `INTGSBTHM193N` | ~1978-01 → ~2021（要確認） | 月次 | % p.a. | ☆☆ |
| th | bond_10y（経路B／現行10Y厳密） | Bank of Thailand（ParYield 10Y） | FRED（OECD MEI再配信） | `IRLTLT01THM156N` | ~2000-04 → 現在 | 月次 | % p.a. | ☆ |
| th | cpi | 商務省貿易政策戦略局（TPSO） | FRED（OECD MEI再配信） | `THACPIALLMINMEI` | ~1985-01 → 現在 | 月次 | 指数（2015=100, NSA） | ☆ |
| th | central_bank_total_assets | Bank of Thailand（EC_MB_011） | **IMF IFS SDMX** または BOT SDW 直接 | IFS: Central Bank Survey, Total Assets, THA | IFS: ~1957- ／ BOT機械可読: 1997-01- | 月次 | THB 百万バーツ | ☆☆ |

**特記事項（th）**

- `policy_rate` は1997年危機を含む1990年代と、現行のBOT政策金利（1日物RP）が**制度的に断絶している**ため、両経路を併記する：
  - **経路A（推奨デフォルト）**：FRED `INTDSRTHM193N`（IMF IFS Discount Rate ＝ BOT Bank Rate）。1990年・1997年スパイク・以降を連続して観察できる。**ただし制度上、これは2000年以降のRPレートそのものではなく、1997年当時の主要政策金利（Bank Rate）を IMF が連続性を保ったまま配信した系列**である。`/data-paths/` で「2000年以前は Bank Rate、2000年以降は IMF が概念的継続性を維持して再配信」と明記すること。FRED の last_updated が古い場合は BIS `cbpol` にフォールバック。
  - **経路B**：BIS `cbpol`（中央銀行政策金利統計、TH 抽出）。1日物RP（2007-）と14日物RP（2000-05〜2007-01）を BIS が継ぎ目なく配信しており、現行レジームの「真の政策金利」として最も厳密。1997年は**カバーしない**。新規 BIS フェッチャが必要。
  - 蒲池さんへの判断材料：本プロジェクトの主眼（Crisis Frontier＝危機兆候観測、1997年が観測対象）からすると **経路A** をデフォルト系列として採用するのが整合的と思われる。経路B は将来 `/data-paths/` ページで補足解説するに留める案を推奨。
- `bond_10y` も同様に2経路：
  - **経路A**：`INTGSBTHM193N`（IMF IFS Government Bonds, Thailand）。**1990年代以前は厳密な10年定常満期利回りではなく、BOTの代表的長期国債利回り**（テナーは時期によって変動）。1997年スパイクは見える。
  - **経路B**：`IRLTLT01THM156N`（OECD MEI 10年ベンチマーク）。2000年4月開始、厳密10Y、`IRLTLT01JPM156N` と方法論的に揃う。**1997年はカバーしない**。
  - 判断材料：本プロジェクトでは **経路A** で1997年を可視化することを優先するのが整合的。`source_note` または `notes` に「2000年以前は厳密10Yではない」旨を記載する。経路Bを将来「現行ベンチマーク用の補助系列」として並べる選択肢は残る。
- `cpi` の `THACPIALLMINMEI` は OECD MEI が TPSO を再配信。タイ国内では基準改定が頻繁（1998, 2002, 2007, 2011, 2015, 2019, 2023）だが OECD 配信は内部でチェインされた連続系列として配信している。1997年危機時の CPI YoY スパイク（1997年初の~5%から1998年中盤の~10%超へ）は完全に捕捉される。`THACPIALLMINMEI` が解決しない場合は `CPALTT01THM661N`（M661N = 指数 2015=100）にフォールバック。
- `central_bank_total_assets`：**FREDにBOTのTotal Assets系列は存在しない**（マネー集計のみ）。FRED `MYAGM1THM189N` 等はマネーストックで負債側であり代替不可。
  - 推奨：**IMF IFS SDMX 経由**（`http://dataservices.imf.org/REST/SDMX_JSON.svc/`、Central Bank Survey、country=THA、Total Assets）。新規 SDMX フェッチャが必要だが、日本・タイで経路を統一でき、将来的に他国（韓国・インドネシアなど）への拡張も同経路で可能。
  - 代替：BOT SDW 直接（テーブル EC_MB_011「Assets and Liabilities of the Bank of Thailand」、Excel/CSV ダウンロード）。1997年以降が機械可読、1942年からの歴史データもアーカイブにあり。
  - **これは資産側Total Assetsであり、BOT のマネタリーベース表（EC_MB_004 系列）や FRED のマネーストック系列は負債側で別物**。

---

## 3. 横断的な観察（設計上の論点）

調査の過程で、yaml 設計に影響しうる構造的論点が3つ浮上した。本フェーズの作業対象外だが、次フェーズでの判断材料として記録する。

### 3.1 取得経路が3種類に分岐する

12枠を「同じ経路で取れるか」で分類すると、次のとおり：

| 経路 | 該当枠数 | 該当枠 |
|---|---:|---|
| FRED 既存フェッチャでそのまま取れる | **9枠** | jp/bond_10y, jp/cpi, jp/fx_reserves, us/bond_10y, us/cpi, us/fx_reserves, us/central_bank_total_assets, th/policy_rate（経路A）, th/bond_10y（経路A or B）, th/cpi |
| **IMF IFS SDMX**（新規フェッチャ） | **1枠** | th/central_bank_total_assets |
| **BOJ stat-search 直接**（新規フェッチャ） | **1枠** | jp/central_bank_total_assets |
| **BIS cbpol**（経路Bを採用する場合のみ） | 0〜1枠 | th/policy_rate（経路Bを採る場合） |

→ 12枠のうち**9枠は既存FRED経路で完結**するが、**残り2枠（jp/th の中央銀行総資産）は新規データソース統合が必要**。`fetch_imf.py` のような新規スクリプトの追加が、次フェーズの実装規模を決める主な要因となる。

### 3.2 「1997年連続性 vs 現行レジーム」が2枠で発生

- `th/policy_rate`（Bank Rate → 14日RP → 1日RP）
- `th/bond_10y`（代表長期金利 → 厳密10Yベンチマーク）

両枠とも、1997年危機の可視化を優先するなら IMF IFS 経路（経路A）、現行レジームの厳密性を優先するなら OECD/BIS 経路（経路B）。本プロジェクトの主眼が Crisis Frontier である以上、**デフォルトは経路A**としつつ、`source_note` または `notes` でレジーム変更を明記し、`/data-paths/` ページで両経路の存在を読者に開示する設計が妥当と思われる。

### 3.3 単位・基準年・季節調整の不揃い

3カ国を並べて表示する際の整合性課題：

| 指標 | 不揃いの種類 | 推奨対処 |
|---|---|---|
| cpi | 米国 1982-84=100、日タイ 2015=100 | YoY% 表示で吸収（描画側で対応） |
| cpi | 米国 SA／日タイ NSA | 米国も `CPIAUCNS`（NSA）採用で揃える |
| bond_10y | 米国は日次、日タイは月次 | 月次にダウンサンプリング、または各国カードで頻度を明示 |
| central_bank_total_assets | 米国 USD百万、日 JPY億円、タイ THB百万 | 自国通貨表示が一次源の慣行。USD換算するか自国通貨のままかは描画フェーズの判断 |

---

## 4. 全体所感：難易度別の整理

### 4.1 すぐに取得作業に入れる枠（難易度☆、9枠）

既存 `fetch_data.py`（FRED）または `fetch_worldbank.py` をそのまま使い、`indicators.yaml` の `data_sources` に1行追加するだけで動く枠。

| 国 | 指標 | 系列ID |
|---|---|---|
| jp | bond_10y | `IRLTLT01JPM156N` |
| jp | cpi | `JPNCPIALLMINMEI` |
| jp | fx_reserves | `TRESEGJPM052N` |
| us | bond_10y | `DGS10` |
| us | cpi | `CPIAUCNS` |
| us | fx_reserves | `TRESEGUSM052N` |
| us | central_bank_total_assets | `WALCL`（ただし2002-12開始） |
| th | policy_rate | `INTDSRTHM193N`（経路A採用時） |
| th | cpi | `THACPIALLMINMEI` |

### 4.2 中程度の作業を要する枠（難易度☆☆、2枠）

新規フェッチャまたは系列の選定判断が必要な枠。

| 国 | 指標 | 必要な作業 |
|---|---|---|
| th | bond_10y | `INTGSBTHM193N`（経路A）採用＋「1990年代は厳密10Yではない」旨の特記事項記載。経路Bを将来併設するか要判断 |
| th | central_bank_total_assets | **IMF IFS SDMX フェッチャの新規実装**（`scripts/fetch_imf.py` 等）。1ヶ国だけのために実装するのは投資対効果が悪いので、jp も同経路に揃える設計判断と一緒に検討すべき |

### 4.3 取得が困難な枠（難易度☆☆☆、1枠）

| 国 | 指標 | 困難の理由・対処案 |
|---|---|---|
| jp | central_bank_total_assets | **FREDに資産側Total Assets系列が存在しない**。BOJ stat-search からの独自フェッチャ実装、または IMF IFS SDMX 経路（タイと統一）を採用する必要がある。後者なら th/central_bank_total_assets と合わせて1本のフェッチャで日タイ両方をカバーでき、設計上の経済性が高い |

### 4.4 蒲池さんに判断を求めたい設計事項（再掲・確認用）

報告書を確認のうえ、次フェーズの作業範囲を確定するために以下の判断をお願いしたい。

1. **th/policy_rate の経路採用**：経路A（`INTDSRTHM193N`、1997カバー）をデフォルトとし、経路B は `/data-paths/` 補足のみとする方針でよいか。
2. **th/bond_10y の経路採用**：同上、経路A（`INTGSBTHM193N`）をデフォルトとし、特記事項で「2000年以前は厳密10Yではない」旨を明記する方針でよいか。
3. **us/central_bank_total_assets の1990年代カバー**：FRED `WALCL` の2002年開始を受け入れ、チャートに注記する方針でよいか。それとも H.4.1 アーカイブから手動継ぎ足しを目指すか。
4. **jp/th 中央銀行総資産の経路統一**：jp は BOJ 直接、th は BOT/IMF IFS という別経路にするか、両国とも IMF IFS SDMX に統一するか。後者なら新規フェッチャ1本で済む。
5. **米国 fx_reserves の `how_to_read` 注記**：米国は構造的指標であり、危機シグナルとしては FRB USD スワップライン（`SWPT`）を別途参照、と注記する方針でよいか。

---

## 5. 参照URL一覧（次回のローカル検証用）

| 系列ID | 確認URL |
|---|---|
| DGS10 | https://fred.stlouisfed.org/series/DGS10 |
| IRLTLT01JPM156N | https://fred.stlouisfed.org/series/IRLTLT01JPM156N |
| INTGSBTHM193N | https://fred.stlouisfed.org/series/INTGSBTHM193N |
| IRLTLT01THM156N | https://fred.stlouisfed.org/series/IRLTLT01THM156N |
| CPIAUCNS | https://fred.stlouisfed.org/series/CPIAUCNS |
| JPNCPIALLMINMEI | https://fred.stlouisfed.org/series/JPNCPIALLMINMEI |
| THACPIALLMINMEI | https://fred.stlouisfed.org/series/THACPIALLMINMEI |
| WALCL | https://fred.stlouisfed.org/series/WALCL |
| TRESEGJPM052N | https://fred.stlouisfed.org/series/TRESEGJPM052N |
| TRESEGUSM052N | https://fred.stlouisfed.org/series/TRESEGUSM052N |
| INTDSRTHM193N | https://fred.stlouisfed.org/series/INTDSRTHM193N |
| BOJ stat-search | https://www.stat-search.boj.or.jp/ |
| BOJ Accounts (EN) | https://www.boj.or.jp/en/statistics/boj/other/acmai/index.htm |
| BOT statistics | https://www.bot.or.th/en/statistics.html |
| BIS cbpol | https://www.bis.org/statistics/cbpol.htm |
| IMF IFS SDMX | http://dataservices.imf.org/REST/SDMX_JSON.svc/ |

---

以上。本報告書の確認後、yaml 反映方針について別途指示をお願いいたします。
