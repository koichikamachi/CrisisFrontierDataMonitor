# データソース調査報告：フェーズ4（韓国・インドネシア・マレーシア）

- **作成日**: 2026-05-17
- **対象**: フェーズ4 — 3カ国 × 6指標 = 18枠の新規取得経路調査
- **依頼書**: [`docs/data_source_research_request_phase4.md`](data_source_research_request_phase4.md)
- **報告書スコープ**: 系列の存在確認のみ。yaml 更新・コード変更・データ取得は本作業に含めない
- **検証方針**: 実APIアクセスで生レスポンスを確認。検証スクリプトは `%TEMP%` に作成・実行・削除（プロジェクトツリーには痕跡を残さない）

---

## 0. このフェーズの位置づけ

Crisis Frontier の研究過程で必要になったデータを整理する中で、同じ問題意識を持つ学生や研究者にも利用可能な観測基盤として整備している。目的は、単なる統計集の作成ではなく、危機の発火・伝播・分岐を比較可能な形で観察することである。なお、Bookkeeping Lens の観点では、数量だけではなく、その背後の関係構造も観測対象となる。

---

## 1. エグゼクティブサマリー

| 国 | 取得可能枠 | 月次経路あり | 1997 月次カバー | プレースホルダ |
|---|---|---|---|---|
| **韓国（kr）** | 6/6 | 6/6 | **5/6**（CB Total Assets のみ 2001-12〜） | 0 |
| **インドネシア（id）** | 5/6 | 5/6 | **4/6**（CB Total Assets 同前、bond_10y は経路なし） | 1（bond_10y） |
| **マレーシア（my）** | 6/6 | 5/6 | **5/6**（CB Total Assets 同前） | 0 |
| **合計** | **17/18** | **16/18** | **14/18** | **1** |

### 主要発見

1. **韓国は理想的な国**: 5/6 指標で 1997 月次カバー、すべて既存フェッチャの data_sources に1行追加で対応可能
2. **タイになかった bond_10y がマレーシアと韓国にはある**:
   - **`MYS.S13BOND_RT_PT_A_PT.M` が IMF SDMX に 1992-M02〜存在**、1997-12=7.745%
   - **`KOR.S13BOND_RT_PT_A_PT.M` は 1990-M01〜存在**、1997-12=15.32%
   - タイは1999-09〜だったが、韓国・マレーシアは1997完全カバー
3. **インドネシアの bond_10y は公開APIに存在しない**: FRED / IMF SDMX / BIS いずれにもなし。タイと同じく「市場の歴史的事実として存在しない」とは異なり、「公開API経路として整備されていない」型の欠落
4. **BIS `WS_XRU`（為替レート専用フロー）の発見**: フェーズ2.5 では使わなかったが、インドネシアの fx_usd（FRED に存在しない）に必須の経路
   - `WS_XRU/M.ID` で IDR/USD 月次 1990-01〜2026-04（1997-12=4650、1997 大暴落観測可能）
   - `WS_XRU/M.MY` で MYR/USD 月次 1990-01〜2026-04（1997-12=3.79、リンギット急落観測可能）
5. **FRED 国コードの罠を回避**: `DEXINUS` は **インド（Indian Rupees）** であってインドネシアではない。誤採用は重大バグになるため確認が必須

---

## 2. 検証方法

### 2-1. 検証スクリプトの作法

第一波〜第三波と同じく、`C:\Users\koich\AppData\Local\Temp\verify_*.py` に検証スクリプトを作成・実行した。プロジェクトツリー（`scripts/`, `config/`）には一切手を加えていない。

### 2-2. 検証経路

各国について以下5系統を実APIで叩いて確認：

- **FRED**: `https://api.stlouisfed.org/fred/series?...&api_key=...&file_type=json`（既存 .env の API キー使用）
- **World Bank**: `https://api.worldbank.org/v2/country/{XXX}/indicator/{ind}?format=json&...`
- **IMF SDMX**: `https://api.imf.org/external/sdmx/2.1/data/IMF.STA,{flow}/{key}?...`
- **OECD SDMX**: `https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,{flow}/{key}?...`
- **BIS SDMX**: `https://stats.bis.org/api/v1/data/BIS,{flow}/{key}?...`

### 2-3. 国コード規約の罠

| 経路 | 韓国 | インドネシア | マレーシア |
|---|---|---|---|
| FRED | series_id 内に **KO** または **KR** | series_id 内に **ID** 等（要注意：`DEXINUS` は India） | series_id 内に **MA** |
| World Bank | `KOR` | `IDN` | `MYS` |
| IMF SDMX | `KOR` | `IDN` | `MYS` |
| OECD SDMX | `KOR` | （非加盟） | （非加盟） |
| BIS SDMX | `KR` | `ID` | `MY` |

---

## 3. 国別 × 指標別の枠ごとの推奨経路表

評価軸: カバー期間 / 信頼性 / 保守性 / 実装難易度
凡例: ☆ = 既存フェッチャに data_sources 1行追加、☆☆ = 既存フェッチャの軽微改修、☆☆☆ = 新規実装

### 3-1. 韓国（kr）

| 指標 | 推奨経路 | series_id | 期間 | 頻度 | 単位 | 1997 | 難易度 |
|---|---|---|---|---|---|---|---|
| fx_usd | FRED | `DEXKOUS` | 1981-04-13 → 2026-05-08 | 日次 | KRW per USD | ✅ | ☆ |
| policy_rate | IMF SDMX | `MFS_IR/KOR.DISR_RT_PT_A_PT.M` | 1990-M01 → 2026-M02 | 月次 | % p.a. | ✅（1997=5%） | ☆ |
| bond_10y | IMF SDMX | `MFS_IR/KOR.S13BOND_RT_PT_A_PT.M` | 1990-M01 → 2026-M02 | 月次 | % p.a. | ✅（1997-12=15.32%） | ☆ |
| cpi | BIS SDMX | `WS_LONG_CPI/M.KR` | 1965-01 → 2026-02 | 月次 | Index 2010=100 | ✅（1997-12=68.32） | ☆ |
| fx_reserves | FRED | `TRESEGKRM052N` | 1950-12 → 2026-03 | 月次 | M USD | ✅（1997=$20.47B） | ☆ |
| central_bank_total_assets | IMF SDMX | `MFS_CBS/KOR.S121_A_TA_ASEC_CB1SR.XDC.M` | 2001-M12 → 2025-M10 | 月次 | KRW | ❌（2001-起点） | ☆ |

**代替経路**（依頼書 6-3 方針に従い併記）:
- **cpi 代替1**: OECD SDMX `OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL/KOR.M.N.CPI.IX._T.N._Z`、1990-01 → 2026-04 月次 Index 2015=100、436件、1997-01=58.81（COICOP 1999 flow。COICOP 2018 flow にはなし）
- **cpi 代替2**: IMF SDMX `CPI/KOR.CPI._T.IX.M` 1990-M01 → 2026-M04, 436件, 1997-M01=46.06（参考値）
- **cpi 年次フォールバック**: World Bank `KOR/FP.CPI.TOTL` 1990-2024、Index 2010=100、1997=65.97
- **bond_10y 代替**: FRED `INTGSBKRM193N` 1973-05〜2026-02、月次（IMF IFS 旧経由）
- **policy_rate 代替**: FRED `INTDSRKRM193N`（Discount Rate）1964-01〜2026-02、月次 / FRED `IRSTCI01KRM156N`（Call Money）1991-01〜2026-04
- **fx_reserves 年次**: World Bank `KOR/FI.RES.TOTL.CD` 1990-2024、年次、1997=$20.47B

**韓国の所感**:
- 全6指標が月次で取れる、5指標で1997カバー成功
- データソース選択肢の多さ（OECD加盟国、IMF系列充実、BIS LONG_CPI 1965〜）から、最も整備しやすい国
- 既存5系統フェッチャの data_sources に1行追加するだけ（追加コード不要）

### 3-2. インドネシア（id）

| 指標 | 推奨経路 | series_id | 期間 | 頻度 | 単位 | 1997 | 難易度 |
|---|---|---|---|---|---|---|---|
| fx_usd | **BIS SDMX** | `WS_XRU/M.ID`（COLLECTION=A, Avg of period）| 1990-01 → 2026-04 | 月次 | IDR per USD | ✅（1997-12=4827） | ☆☆ |
| policy_rate | FRED | `IRSTCI01IDM156N` | 1990-01 → 2026-04 | 月次 | %（Call Money/Interbank Rate）| ✅ | ☆ |
| **bond_10y** | **（経路なし）** | — | — | — | — | — | プレースホルダ |
| cpi | BIS SDMX | `WS_LONG_CPI/M.ID` | 1979-01 → 2026-01 | 月次 | Index 2010=100 | ✅（1997-12=23.11） | ☆ |
| fx_reserves | FRED | `TRESEGIDM052N` | 1950-12 → 2026-03 | 月次 | M USD | ✅（1997=$17.49B） | ☆ |
| central_bank_total_assets | IMF SDMX | `MFS_CBS/IDN.S121_A_TA_ASEC_CB1SR.XDC.M` | 2001-M12 → 2026-M02 | 月次 | IDR | ❌（2001-起点） | ☆ |

**fx_usd 経路の注意点（重要）**:
- FRED の `DEXINUS` は **India（インド）の Indian Rupees** であってインドネシアではない。誤採用は重大バグ。インドネシアの IDR/USD は **FRED に存在しない**
- 代替で BIS `WS_XRU` を採用。フェーズ2.5 では使わなかった BIS データフローのため、`fetch_bis.py` の **UNIT_MEASURE フィルタ条件を可変化する軽微改修**が必要（現状 `UNIT_MEASURE=628` で固定、WS_XRU は別の単位概念）→ **難易度 ☆☆**

**bond_10y の経路欠落**:
- IMF SDMX MFS_IR に `IDN.S13BOND_RT_PT_A_PT.M` は存在しない（FRED 全候補・BIS WS_LTBY 旧フローもなし）
- インドネシアの10年国債利回りは公開API経路として整備されていない
- 一次源（Bank Indonesia）のスクレイピングは本フェーズの目標外（依頼書 8 節）
- → 依頼書 2-1 方針「欠損枠はプレースホルダで残す、`how_to_read` に『データソース未確定』と注記」に基づき**プレースホルダ枠**として扱う

**代替経路**:
- **fx_usd 年次フォールバック**: World Bank `IDN/PA.NUS.FCRF` 1990-2024、年次、1997=2909.38
- **cpi 代替1**: FRED `IDNCPIALLMINMEI` 1968-01 → 2025-04 月次 Index 2015=100
- **cpi 代替2**: IMF SDMX `CPI/IDN.CPI._T.IX.M` 1990-M01 → 2026-M04, 436件, 1997-01=13.26
- **cpi 年次**: World Bank `IDN/FP.CPI.TOTL` 1990-2024、1997=22.24
- **fx_reserves 年次**: World Bank `IDN/FI.RES.TOTL.CD` 1990-2024、1997=$17.49B
- **policy_rate 代替**: IMF SDMX `MFS_IR/IDN.MFS166_RT_PT_A_PT.M` (Monetary policy-related rate) 1990-M01 → 2026-M02
- **bond_10y 補完（年次・近接概念）**: World Bank `IDN/FR.INR.LEND`（Lending Rate）1997=21.82%（参考）

**インドネシアの所感**:
- 5/6 指標で月次取得可能、4指標で1997カバー
- **bond_10y は唯一の真の欠落枠**: 公開API経路がなく、フェーズ4 ではプレースホルダ対応
- fx_usd の BIS WS_XRU 採用に伴い `fetch_bis.py` の軽微改修が必要

### 3-3. マレーシア（my）

| 指標 | 推奨経路 | series_id | 期間 | 頻度 | 単位 | 1997 | 難易度 |
|---|---|---|---|---|---|---|---|
| fx_usd | FRED | `DEXMAUS` | 1971-01-04 → 2026-05-08 | 日次 | MYR per USD | ✅ | ☆ |
| policy_rate | IMF SDMX | `MFS_IR/MYS.MMRT_RT_PT_A_PT.M` （Money Market Rate）| 1990-M01 → 2026-M03 | 月次 | % p.a. | ✅（1997-12=8.295%） | ☆ |
| bond_10y | IMF SDMX | `MFS_IR/MYS.S13BOND_RT_PT_A_PT.M` | 1992-M02 → 2026-M03 | 月次 | % p.a. | ✅（1997-12=7.745%） | ☆ |
| cpi | BIS SDMX | `WS_LONG_CPI/M.MY` | 1968-01 → 2026-03 | 月次 | Index 2010=100 | ✅（1997-12=74.29） | ☆ |
| fx_reserves | World Bank | `MYS/FI.RES.TOTL.CD` | 1990 → 2024 | **年次** | USD | ✅（1997=$21.47B） | ☆ |
| central_bank_total_assets | IMF SDMX | `MFS_CBS/MYS.S121_A_TA_ASEC_CB1SR.XDC.M` | 2001-M12 → 2026-M01 | 月次 | MYR | ❌（2001-起点） | ☆ |

**policy_rate の特記事項**:
- IMF SDMX MFS_IR に `MYS.DISR_RT_PT_A_PT.M`（公定歩合）は**欠落**。タイ・韓国にはあったがマレーシアにはない
- `MYS.MFS166_RT_PT_A_PT.M`（Monetary policy-related rate）は 2001-M12〜のみ → 1997 月次カバーせず
- → **`MYS.MMRT_RT_PT_A_PT.M`（Money Market Rate）を policy_rate の実質的代替として採用**。1990-M01〜2026-M03、1997 月次完全カバー。Bank Negara Malaysia の Overnight Policy Rate (OPR) を含むコールマネー市場金利

**fx_reserves の特記事項**:
- FRED に `TRESEGMYM052N` が**存在しない**。韓国・インドネシアにはあるがマレーシアにはない
- → **月次経路がない**ため、World Bank 年次のフォールバックを採用
- これは依頼書 6-3 方針「同一系列について月次と年次の両経路がある場合は両方を報告書に併記」の特殊ケース：月次がない場合は年次のみ

**代替経路**:
- **fx_usd 月次**: BIS SDMX `WS_XRU/M.MY` 1990-01 → 2026-04、月次、1997-12=3.79（fetch_bis.py 改修と同じく ☆☆ 相当だが、FRED 日次の方が情報密度高いため日次を主推奨）
- **cpi 年次**: World Bank `MYS/FP.CPI.TOTL` 1990-2024、Index 2010=100、1997=73.32
- **bond_10y 補完（年次・近接概念）**: World Bank `MYS/FR.INR.LEND` 1997=10.63%（参考）

**マレーシアの所感**:
- 6/6 指標で取得経路あり、5指標で月次経路、1指標（fx_reserves）が年次のみ
- 5指標で 1997 月次カバー
- タイにも韓国にもなかった **`MYS.S13BOND_RT_PT_A_PT.M`** が IMF SDMX に存在することが最大の発見
- policy_rate に MMRT_RT を採用する判断は実装計画段階での再確認推奨

---

## 4. 全体所感（フェーズ4 実装計画への示唆）

### 4-1. 取得難易度の分布

| 難易度 | 枠数 | 内容 |
|---|---|---|
| ☆ | 15 / 18 | 既存フェッチャ（fetch_data.py、fetch_worldbank.py、fetch_imf.py、fetch_bis.py、fetch_oecd.py）の data_sources に1行追加で対応可 |
| ☆☆ | 2 / 18 | `fetch_bis.py` の UNIT_MEASURE フィルタを可変化する軽微改修が必要（id/fx_usd, my/fx_usd 代替経路） |
| ☆☆☆ | 0 / 18 | 新規フェッチャ実装は不要 |
| プレースホルダ | 1 / 18 | id/bond_10y（公開API経路なし） |

### 4-2. fetch_bis.py の軽微改修について

現状 `fetch_bis.py` は WS_LONG_CPI 専用にハードコードされた `UNIT_MEASURE_FILTER = "628"` で系列を絞り込んでいる。`WS_XRU`（為替レート）には UNIT_MEASURE 概念がなく、代わりに `COLLECTION`（A=Average, E=End of period）で系列を絞る必要がある。

改修案：
- yaml の data_sources エントリに `filter` フィールドを追加し、各エントリで任意の属性=値を指定できるようにする
- 例: `series_id: WS_XRU/M.ID` + `filter: {COLLECTION: A}`
- これによりフィルタ条件を data_sources 側に持たせ、fetch_bis.py 本体はソース非依存に

実装上は単純（30〜50行程度の追加）。

### 4-3. 推奨される実装波構成

依頼書 9 節「実装は波状導入を許容する」に基づき、3波構成を推奨：

#### 第一波（韓国 6枠 + インドネシア・マレーシア の難易度 ☆ 枠を一斉投入）

- **韓国 6枠すべて** (DEXKOUS, MFS_IR/KOR.DISR_RT, MFS_IR/KOR.S13BOND_RT, WS_LONG_CPI/M.KR, TRESEGKRM052N, MFS_CBS/KOR.S121)
- **インドネシア**: policy_rate, cpi, fx_reserves, central_bank_total_assets の 4枠
- **マレーシア**: fx_usd (FRED), policy_rate, bond_10y, cpi, fx_reserves (WB年次), central_bank_total_assets の 6枠

合計 **16枠**を1コミットで投入。第二波の `feat(phase-2.5): add IMF SDMX fetcher (3 slots: ...)` と同じ粒度。

#### 第二波（fetch_bis.py の軽微改修 + WS_XRU 経路）

- `fetch_bis.py` の UNIT_MEASURE フィルタを yaml-driven な `filter` 辞書に拡張
- インドネシア fx_usd: `WS_XRU/M.ID` + `filter: {COLLECTION: A}`
- マレーシア fx_usd 代替経路（推奨は FRED DEXMAUS のままだが、BIS WS_XRU も実装可能であれば併記）

合計 **1〜2枠** + フェッチャ改修1ファイル。

#### 第三波（bond_10y プレースホルダ整備）

- インドネシア bond_10y 用のプレースホルダ枠を yaml に追加（取得経路なし）
- `how_to_read_country_specific.id` に「データソース未確定」注記を追加（フェーズ2.5 (C) で導入したスキーマを活用）
- 報告書のプロジェクト全体方針として「インドネシア10年国債利回りは公開API経路なし、フェーズ5以降の一次源直接アクセス（Bank Indonesia）で再評価」を明記

合計 **1枠**（プレースホルダ + 文書注記）。

---

## 5. データソース別の利用統計（フェーズ4 で追加される枠）

| ソース | 韓国 | インドネシア | マレーシア | 計 |
|---|---|---|---|---|
| FRED | 2 (fx_usd, fx_reserves) | 2 (policy_rate, fx_reserves) | 1 (fx_usd) | 5 |
| World Bank | — | — | 1 (fx_reserves 年次) | 1 |
| IMF SDMX | 3 (policy_rate, bond_10y, CBTA) | 1 (CBTA) | 3 (policy_rate, bond_10y, CBTA) | 7 |
| BIS SDMX (LONG_CPI) | 1 (cpi) | 1 (cpi) | 1 (cpi) | 3 |
| BIS SDMX (WS_XRU 新規) | — | 1 (fx_usd) | — | 1 |
| OECD SDMX | （代替併記のみ） | — | — | 0 |
| 経路なし（プレースホルダ） | 0 | 1 (bond_10y) | 0 | 1 |
| **計** | **6** | **6** | **6** | **18** |

OECD SDMX は韓国 CPI の代替併記としてのみ報告書に記録（推奨経路は BIS WS_LONG_CPI）。

---

## 6. 1997 年カバー状況のまとめ

| 国 / 指標 | fx_usd | policy_rate | bond_10y | cpi | fx_reserves | CBTA |
|---|---|---|---|---|---|---|
| kr | ✅ | ✅ | ✅ | ✅ | ✅ | ❌（2001-） |
| id | ✅ | ✅ | ❌（経路なし） | ✅ | ✅ | ❌（2001-） |
| my | ✅ | ✅（MMRT 採用） | ✅ | ✅ | ✅（年次） | ❌（2001-） |

**1997 カバー率**: 14 / 18 = 78%（CB Total Assets の構造的制約 3枠 + id/bond_10y のプレースホルダ 1枠を除く）

特筆すべき1997期サンプル値：
- **kr/bond_10y 1997-12 = 15.32%** ← 韓国の通貨危機期、金利急騰が完全観測可能
- **id/cpi 1997-12 = 23.11** vs 1997-01 = 20.92 ← インドネシアのインフレ加速
- **my/fx_usd 1997-12 = 3.79 (BIS)** vs 1997-01 = 2.49 ← リンギット 52% 切り下げが観測可能
- **kr/policy_rate (Discount Rate) 1997-12 = 5%** ← 政策的低位（実際の市場金利は急騰、Money Market Rate 1997-12=21.58%）
- **id/fx_usd (BIS) 1997-12 = 4650** vs 1997-01 = 2370 ← ルピア急落

これらは Crisis Frontier 研究の「危機境界」観測点として極めて貴重なデータ。

---

## 7. 参照URL（2026-05-17 時点）

| 用途 | URL |
|---|---|
| FRED 系列メタデータ照会 | `https://api.stlouisfed.org/fred/series?series_id={SID}&api_key={KEY}&file_type=json` |
| World Bank 指標取得 | `https://api.worldbank.org/v2/country/{ISO3}/indicator/{IND}?format=json&date=1990:2025&per_page=500` |
| IMF SDMX MFS_IR（金利） | `https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_IR/{ISO3}.{INDICATOR}.M` |
| IMF SDMX MFS_CBS（CB B/S） | `https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_CBS/{ISO3}.S121_A_TA_ASEC_CB1SR.XDC.M` |
| IMF SDMX CPI | `https://api.imf.org/external/sdmx/2.1/data/IMF.STA,CPI/{ISO3}.CPI._T.IX.M` |
| BIS WS_LONG_CPI | `https://stats.bis.org/api/v1/data/BIS,WS_LONG_CPI/M.{ISO2}` |
| **BIS WS_XRU**（為替、新規発見） | `https://stats.bis.org/api/v1/data/BIS,WS_XRU/M.{ISO2}` |
| OECD SDMX CPI（COICOP 1999） | `https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL/{ISO3}.M.N.CPI.IX._T.N._Z` |

---

## 8. 次のアクション（本作業の射程外、ユーザ判断待ち）

1. 本報告書の確認
2. 確認後、第一波実装計画の提示（韓国 6枠 + IDN/MY の難易度 ☆ 枠を一括投入）
3. 第一波実装後、第二波（fetch_bis.py 軽微改修 + WS_XRU 経路）の提示
4. 第三波（id/bond_10y プレースホルダ整備、how_to_read 注記）
5. 各波で yaml 反映、コード変更、コミット、push はそれぞれユーザ確認を経る

以上、本報告書はここまで。
