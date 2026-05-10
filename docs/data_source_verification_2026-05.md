# データソース調査 補遺 — 2026-05-10 ローカル検証結果

- **作成日**: 2026-05-10
- **対象**: 第二波（fetch_imf.py 実装）の事前検証
- **位置づけ**: **本書は元報告書 [`data_source_research_2026-05.md`](data_source_research_2026-05.md) の前提変更を記録する補遺である**。元報告書は2026-05-09時点での外部API構造を前提に書かれたが、2026-05-10のローカル検証で複数の前提が崩れたため、本補遺で確定情報を上書きする

---

## 0. 検証の動機と方法

第二波（jp/cpi、jp/central_bank_total_assets、th/cpi、th/policy_rate、th/bond_10y、th/central_bank_total_assets の6枠）を IMF IFS SDMX 経由で取得する設計を、`fetch_imf.py` 実装着手前に検証した。

第一波の動作確認で「FRED に存在するはずの系列が実際には消えていた」事案（タイ全枠・JP CPI が観測停止）が発生したため、IMF IFS SDMX についても同様のリスクを潰すことを目的とする。

検証スクリプトは `%TEMP%` に作成・実行・削除した（プロジェクトツリーには痕跡を残さない方針、第一波と同じ作法）。

---

## 1. 重大な前提変更

### 1-1. 旧エンドポイント `dataservices.imf.org` は廃止済み

```
nslookup dataservices.imf.org
→ Non-existent domain
```

元報告書セクション5で参照URLとして掲載した `http://dataservices.imf.org/REST/SDMX_JSON.svc/` は、2024年頃にIMFがサービス移行した際に廃止されている。DNS自体が解決しない。

### 1-2. 現行エンドポイント

```
https://api.imf.org/external/sdmx/2.1/
```

SDMX 2.0 から SDMX 2.1 への規格移行と同時に、ポータル構造が再設計されている。

### 1-3. 「IFS」という単一データフローは存在しない

旧API では `IFS` データセット下に各種マクロ系列が集約されていたが、新ポータルでは **193個のトピック別データフロー**に分割された。第二波の6枠に関わるデータフローは次のとおり：

| Dataflow | DSD | 次元（順序） | 用途 |
|---|---|---|---|
| `CPI` | DSD_CPI | COUNTRY.INDEX_TYPE.COICOP_1999.TYPE_OF_TRANSFORMATION.FREQUENCY | CPI |
| `MFS_IR` | DSD_MFS_IR | COUNTRY.INDICATOR.FREQUENCY | 政策金利・市場金利・国債利回り |
| `MFS_FMP` | DSD_MFS_FMP | COUNTRY.INDICATOR.TYPE_OF_TRANSFORMATION.FREQUENCY | 株価指数等（実質ここに国債は無い） |
| `MFS_CBS` | DSD_MFS_CBS | COUNTRY.INDICATOR.TYPE_OF_TRANSFORMATION.FREQUENCY | 中央銀行 Balance Sheet |
| `IRFCL` | DSD_IRFCL_PUB | COUNTRY.INDICATOR.SECTOR.FREQUENCY | 国際準備（参考） |

### 1-4. 国コードは 3文字 ISO（alpha-3）

旧 IFS では2文字コード（`TH`, `JP`）が使われていたが、新ポータルでは **`THA`, `JPN`** の3文字 ISO（alpha-3）。これに気付かないと全クエリが空応答になる。

### 1-5. レスポンスは XML（StructureSpecificData）

JSON Accept ヘッダー（`application/vnd.sdmx.data+json`）は本検証時点では効かず、SDMX 2.1 XML レスポンスが返る。`fetch_imf.py` は `xml.etree.ElementTree` を使う前提で実装する。

---

## 2. 6枠の系列実在確認結果

### 2-1. サマリー

| # | 枠 | 推奨系列 | キー（クエリ用） | 期間 | 件数 | 1997カバー | 単位 | 評価 |
|---|---|---|---|---|---|---|---|---|
| 1 | **th/policy_rate** | `DISR_RT_PT_A_PT`（Discount Rate） | `THA.DISR_RT_PT_A_PT.M`（MFS_IR） | **1990-M01 → 2026-M03** | 435 | **✅** | % p.a. | **完全採用可** |
| 2 | th/bond_10y | `S13BOND_RT_PT_A_PT`（Government bonds, generic） | `THA.S13BOND_RT_PT_A_PT.M`（MFS_IR） | 1999-M09 → 2026-M03 | 319 | ❌ | % p.a. | 1997欠落、第三波で別経路 |
| 3 | th/cpi | `THA.CPI.CP01.IX.M` 等（COICOP分類別） | CPIフロー | **2010-M01** → 2026-M03 | 195 | ❌ | Index | **1997欠落、第三波で別経路** |
| 4 | jp/cpi | （JPN CPI） | CPIフロー | 1990-M01 → 2026-M03（メタのみ） | 435 | △ | (Index想定) | **OBS_VALUEが空。実データ未投入。採用不可** |
| 5 | th/central_bank_total_assets | `S121_A_TA_ASEC_CB1SR`（Total Assets） | `THA.S121_A_TA_ASEC_CB1SR.XDC.M`（MFS_CBS） | 2001-M12 → 2025-M12 | 289 | ❌ | THB（XDC=自国通貨） | 2001以降のみ、採用可 |
| 6 | jp/central_bank_total_assets | `S121_A_TA_ASEC_CB1SR`（Total Assets） | `JPN.S121_A_TA_ASEC_CB1SR.XDC.M`（MFS_CBS） | 2001-M12 → 2026-M02 | 291 | ❌ | JPY（XDC=自国通貨） | 2001以降のみ、採用可 |

### 2-2. Thailand の MFS_IR 系列8本（参考全列挙）

`THA..M`（COUNTRY=THA, INDICATOR=*, FREQUENCY=M）で取得した全系列：

| INDICATOR | 期間 | 件数 | 内容 | 採用 |
|---|---|---|---|---|
| `DISR_RT_PT_A_PT` | 1990-M01 → 2026-M03 | 435 | **Discount Rate** | **本枠採用** |
| `MFS162_RT_PT_A_PT` | 1990-M01 → 2026-M01 | 408 | Lending Rate | — |
| `MFS135_RT_PT_A_PT` | 1990-M01 → 2026-M01 | 408 | Deposit Rate | — |
| `MMRT_RT_PT_A_PT` | 1990-M01 → 2026-M03 | 435 | Money Market Rate | — |
| `MFS166_RT_PT_A_PT` | 2000-M05 → 2025-M12 | 308 | Monetary policy-related rate（1997欠落） | 不採用 |
| `MFS174_RT_PT_A_PT` | 1999-M01 → 2026-M03 | 327 | Savings Rate | — |
| `S13BOND_RT_PT_A_PT` | 1999-M09 → 2026-M03 | 319 | Government bonds yield | (th/bond_10y第三波の参考) |
| `GSTBILY_RT_PT_A_PT` | 2001-M02 → 2026-M03 | 302 | Treasury bills yields | — |

### 2-3. jp/cpi の特異な状態

新IMF SDMX の CPI フローでは、JPN CPI のメタデータ（時間軸、COICOP_1999 分類）は1990-M01から宣言されているが、**`<Obs>` 要素に `OBS_VALUE` 属性が存在しない**。次のような空観測が435件並ぶ：

```xml
<Series COUNTRY="JPN" INDEX_TYPE="CPI" COICOP_1999="CP01" TYPE_OF_TRANSFORMATION="IX" FREQUENCY="M">
  <Obs TIME_PERIOD="1990-M01" REFERENCE_PERIOD="2015A" DERIVATION_TYPE="O"/>
  <Obs TIME_PERIOD="1990-M02" REFERENCE_PERIOD="2015A" DERIVATION_TYPE="O"/>
  ...
```

参考としてTHA CPI は2010-M01から実値が入っており、構造的問題ではなくJPNデータの未投入と推定される。理由は次のいずれかが想定される：

- IMF 側でJPN CPIデータの投入が未完了
- 日本のCPIは別経路（OECD直接など）に切り出されている
- 日本側の統計局が新フォーマットでの提出を未実施

いずれにせよ、本フェーズでは **jp/cpi は IMF SDMX 経路で取得不可** として扱う。

### 2-4. 中央銀行 Total Assets の構造

MFS_CBS は SNA 風の粒度の細かい資産・負債項目（1020コード）を提供するが、その中に **`S121_A_TA_ASEC_CB1SR`（Assets, Total Assets, All sectors）という単一の合計コード**が存在する。これにより、個別項目を合算する必要なく、Total Assets を直接取得できる。

ただし、データ自体は両国とも **2001-M12 から開始**。MFS 統計枠組み自体が2001年以降のグローバル統一フォーマットによるもので、それ以前の遡及データは新ポータルには含まれていない。

これは元報告書セクション2.1 / 2.3 における「IMF IFS は1957年から」という記述（旧IFSの古い定義に基づく）とは整合しない。新ポータルの MFS_CBS は2001年起点の事実上別系列である。

---

## 3. 第二波（fetch_imf.py）の射程確定

### 3-1. 採用する3枠（論点A：案A1）

| # | 国/指標 | dataflow | キー | 期間 | 単位 |
|---|---|---|---|---|---|
| 1 | th/policy_rate | MFS_IR | `THA.DISR_RT_PT_A_PT.M` | 1990-M01 → 2026-M03 | % p.a. |
| 2 | th/central_bank_total_assets | MFS_CBS | `THA.S121_A_TA_ASEC_CB1SR.XDC.M` | 2001-M12 → 2025-M12 | THB |
| 3 | jp/central_bank_total_assets | MFS_CBS | `JPN.S121_A_TA_ASEC_CB1SR.XDC.M` | 2001-M12 → 2026-M02 | JPY |

### 3-2. 第三波に押し出す3枠

| 国/指標 | 第三波での候補経路 | 課題 |
|---|---|---|
| jp/cpi | OECD SDMX、e-Stat、BOJ stat-search | IMF SDMX は値が未投入、別経路必須 |
| th/cpi | MOC Thailand 直接、World Bank年次（暫定） | 1997カバーには MOC 直接が必要 |
| th/bond_10y | BIS、BOT 直接 | 1999年以降は IMF にあるが1997カバーには別経路 |

### 3-3. 1997年連続性の方針（論点B）

論点Bの判断に基づき、系列ごとに現実的に対応する：

| 系列 | 1997カバー | 採用方針 |
|---|---|---|
| th/policy_rate | ✅ IMF SDMX で1997カバー | 確保 |
| jp/central_bank_total_assets | ❌ 2001以降のみ | **構造的制約として受容**（米国 WALCL も2002以降であり、各国共通の制約） |
| th/central_bank_total_assets | ❌ 2001以降のみ | **構造的制約として受容** |
| th/cpi | — | 第三波で別経路追求 |
| th/bond_10y | — | 第三波で別経路（BIS, BOT直接） |
| jp/cpi | — | 第三波で別経路 |

### 3-4. 単位整合の方針（論点D）

中央銀行 Total Assets は IMF MFS_CBS から **自国通貨建て（XDC = JPY, THB）** で取得し、**米国 WALCL は USD のまま**とする。

各指標カードの `how_to_read` セクションに次の旨を明記する（具体文言は yaml 反映時に確定）：

> 単位は各国の自国通貨建てであり、国際比較する場合は為替やGDP比への換算が別途必要

これは Crisis Frontier 研究の素材として観察する場合、**通貨単位を変換せず一次源の単位で記録する**のが原則であることに沿う。USD換算は描画フェーズで必要に応じて行う。

---

## 4. 元報告書からの主な前提変更

| 元報告書の記述 | 検証で判明した事実 |
|---|---|
| 推奨経路：`http://dataservices.imf.org/REST/SDMX_JSON.svc/` | **エンドポイント廃止**。現行は `https://api.imf.org/external/sdmx/2.1/` |
| IFS database 経由で `M.{country}.{indicator}` の3次元キー | **IFS という単一フローは存在せず**、CPI/MFS_DC/MFS_IR/MFS_FMP/MFS_CBS/IRFCL等の193トピック別フロー |
| 国コードは2文字（TH, JP） | **3文字 ISO（THA, JPN）** |
| JSON で取得 | **XML（SDMX 2.1 StructureSpecificData）** |
| jp/cpi は IMF IFS SDMX で月次連続取得可能 | **値が未投入**。別経路必須 |
| th/cpi は IMF IFS SDMX で1997含む月次取得可能 | **2010-M01以降のみ**。1997カバーには別経路必須 |
| th/bond_10y は IMF IFS Government Bonds で1997カバー（INTGSBTHM193N相当） | **1999-M09以降のみ**。1997カバーには別経路必須 |
| 中央銀行 Total Assets は IMF IFS で1957年以降 | **MFS_CBS は2001-M12以降のみ**（フレームワーク統一の起点） |

---

## 5. 第三波（残り3枠）に向けた検討課題

第二波（fetch_imf.py）完了後の第三波で、jp/cpi、th/cpi、th/bond_10y の経路を整備する。本補遺の段階では**未調査**だが、想定経路は次のとおり：

- **jp/cpi**：OECD SDMX（`https://sdmx.oecd.org/`）、または総務省統計局 e-Stat API（`https://api.e-stat.go.jp/`）
- **th/cpi**：MOC Thailand TPSO（`http://www.price.moc.go.th/`）、または World Bank 年次への暫定退避
- **th/bond_10y**：BIS Statistics（`https://www.bis.org/statistics/`）、または BOT Statistical Data Warehouse（`https://www.bot.or.th/en/statistics.html`）

第三波着手時は、本補遺と同じ作法（`%TEMP%` の検証スクリプトで実在確認 → 結果を新補遺ファイルに記録）で進める。

---

## 6. 参照URL（2026-05-10時点）

| 用途 | URL |
|---|---|
| IMF SDMX 2.1 ルート | https://api.imf.org/external/sdmx/2.1/ |
| dataflow 一覧 | https://api.imf.org/external/sdmx/2.1/dataflow |
| MFS_IR DataStructure | https://api.imf.org/external/sdmx/2.1/dataflow/IMF.STA/MFS_IR?references=datastructure |
| MFS_CBS DataStructure | https://api.imf.org/external/sdmx/2.1/dataflow/IMF.STA/MFS_CBS?references=datastructure |
| MFS_IR THA monthly（全系列） | https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_IR/THA..M?startPeriod=1990&endPeriod=2026 |
| MFS_CBS THA monthly（全系列） | https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_CBS/THA...M?startPeriod=1990&endPeriod=2026 |
| MFS_CBS JPN monthly（全系列） | https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_CBS/JPN...M?startPeriod=1990&endPeriod=2026 |
| MFS_CBS Total Assets THA直接 | https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_CBS/THA.S121_A_TA_ASEC_CB1SR..M |
| MFS_IR Discount Rate THA直接 | https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_IR/THA.DISR_RT_PT_A_PT.M |

---

以上。本補遺の確認後、`fetch_imf.py` 実装計画の提示に進む。
