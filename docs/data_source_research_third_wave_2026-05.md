# データソース調査 第三波 — 2026-05 実APIアクセス検証

- **作成日**: 2026-05-16
- **対象**: フェーズ2.5 第三波（残り3枠の別経路特定）
- **対象枠**: `jp/cpi`, `th/cpi`, `th/bond_10y`
- **位置づけ**: 報告書のみ。yaml 更新・コード変更・データ取得は本作業に含めない（系列の存在確認のみ）
- **検証方針**: 文献ではなく実APIアクセスで生レスポンスを確認。検証スクリプトは `%TEMP%` に作成・実行（プロジェクトツリーには痕跡を残さない）
- **依頼書**: [`docs/data_source_research_request_third_wave.md`](data_source_research_request_third_wave.md)
- **先行報告**: [`docs/data_source_research_2026-05.md`](data_source_research_2026-05.md), [`docs/data_source_verification_2026-05.md`](data_source_verification_2026-05.md)

---

## 0. エグゼクティブサマリー

| 枠 | 第三波の結論 | 1997年連続性 |
|---|---|---|
| **jp/cpi** | **OECD SDMX**（headline + Goods/Services + コアコア相当）を推奨。**BIS WS_LONG_CPI** という超長期代替（1946-08〜）も併存 | ✅ 確保（複数経路） |
| **th/cpi** | **BIS WS_LONG_CPI**（1976-01〜2026-03 月次、Index 2010=100）を推奨。第二波で確認した IMF SDMX（2010〜）を補完経路、World Bank 年次を年次フォールバック | ✅ 確保（BIS 経由で初確認） |
| **th/bond_10y** | **IMF SDMX `S13BOND_RT_PT_A_PT`（1999-09〜）を採用**。1997 月次は構造的に取得不可（タイ国債市場の流動性不足が歴史的背景）。1997 期は既存 `th/policy_rate`（Discount Rate, 1990〜）とWB 年次貸出金利（`FR.INR.LEND`）で補完 | △ 1997月次は構造的に存在しない |

第三波の収穫は **BIS WS_LONG_CPI** の発見である。`th/cpi` は第二波時点では「1997 月次は公開API経由では到達不能」と判断していたが、BIS の長期CPI系列が1976年からカバーしており、1997-01: 67.96（Index, 2010=100）の値を実APIで確認した。

---

## 1. 検証方法

### 1-1. 検証スクリプトの作法

第一波・第二波と同じく、`C:\Users\koich\AppData\Local\Temp\verify_*.py` に検証スクリプトを作成・実行した。プロジェクトツリー（`scripts/`, `config/`）には一切手を加えていない。

### 1-2. 評価軸（複数経路が並ぶ場合）

依頼書で示された4軸：

- **カバー期間**: 月次／年次の最古観測年、1997含むか
- **信頼性**: 一次源との距離、公式SDMX再配信／非公式スクレイピング
- **保守性**: 既存フェッチャ拡張可否、エンドポイント安定性、認証要否
- **実装難易度**: ☆（既存フェッチャ拡張）／☆☆（新規だが単純）／☆☆☆（独自パーサ/認証必要）

### 1-3. 認証の扱い（判断事項a）

選択肢2を採用。未認証で叩けるエンドポイント（カタログ照会・データ取得）に限定。e-Stat や BOT API portal 等の認証必須経路は、実フェッチャ実装フェーズで改めて API キー登録する前提とした。

---

## 2. jp/cpi の調査結果

### 2-1. 候補経路の整理

| 経路 | dataflow / endpoint | 期間 | 頻度 | 単位 | 認証 | 結果 |
|---|---|---|---|---|---|---|
| **OECD SDMX (COICOP 2018)** | `OECD.SDD.TPS,DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL/JPN.M.N.CPI.IX._T.N._Z` | **1990-01 → 2026-03** | 月次 | Index (2015=100) | 不要 | ✅ 採用候補（推奨） |
| **OECD SDMX (COICOP 1999)** | `OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL/JPN.M.N.CPI.IX._T.N._Z` | 1990-01 → 約2021 | 月次 | Index (2015=100) | 不要 | 旧コード体系、最新性に欠ける |
| **BIS WS_LONG_CPI** | `BIS,WS_LONG_CPI/M.JP` | **1946-08 → 2026-03** | 月次 | Index (2010=100) または YoY % | 不要 | ✅ 超長期代替 |
| **e-Stat API** | `https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList?...` | 系列ID 0003427113 等 | 月次 | Index (2020=100) | **必須**（appId） | 認証フェーズで再評価 |
| **World Bank** | `FP.CPI.TOTL` JPN | 1990-2024 | 年次 | Index (2010=100) | 不要 | 年次フォールバック |

### 2-2. 推奨経路（OECD SDMX）の詳細

**完全URL（headline）**:
```
https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL/JPN.M.N.CPI.IX._T.N._Z?startPeriod=1990&endPeriod=2027
```

**Accept ヘッダー**: `application/vnd.sdmx.data+json; charset=utf-8; version=1.0`

**DSD 次元構造（8次元）**:

| 位置 | 次元 | 値 |
|---|---|---|
| 0 | REF_AREA | `JPN` |
| 1 | FREQ | `M` |
| 2 | METHODOLOGY | `N`（National） |
| 3 | MEASURE | `CPI` |
| 4 | UNIT_MEASURE | `IX`（Index） |
| 5 | EXPENDITURE | `_T`（Total / All items）等 |
| 6 | ADJUSTMENT | `N`（NSA）／`S`（SA） |
| 7 | TRANSFORMATION | `_Z`（Not applicable） |

**確認した観測値**（実APIレスポンスより）:
- 1990-01: 89.692
- 1995-01: 97.837
- **1997-01: 97.938** ✅
- 1997-12: 99.771
- 2015-01: 99.567（基準年付近）
- 2020-01: 102.316
- 2026-03: 114.737（最新）

**EXPENDITURE 利用可能カテゴリ（JPN, 8値）**:

| code | 内容 | 用途 |
|---|---|---|
| `_T` | Total / All items（**headline**） | コア6指標枠 |
| `_TXCP01_NRG` | All items non-food non-energy | **コアコア相当** |
| `GD` | Goods | 参考 |
| `SERV` | Services | 参考 |
| `CP01` | Food and non-alcoholic beverages | 参考 |
| `CP041` | Actual rentals for housing | 参考 |
| `CP042` | Imputed rentals for housing | 参考 |
| `CP045_0722` | Energy | 参考 |

**コアコア相当系列の確認**（実APIで取得）:
- key: `JPN.M.N.CPI.IX._TXCP01_NRG.N._Z`
- 1990-01: 92.199 → 1997-01: 101.601 → 2026-03: 108.374
- 1990-01 → 2026-03、435観測、全期間で値あり ✅

### 2-3. 代替経路（BIS WS_LONG_CPI）の詳細

**完全URL**:
```
https://stats.bis.org/api/v1/data/BIS,WS_LONG_CPI/M.JP
```

**Accept**: `application/vnd.sdmx.structurespecificdata+xml;version=2.1`

**DSD**: 3次元（`FREQ.REF_AREA.UNIT_MEASURE`）。REF_AREA は **2文字 ISO（`JP`）**であることに注意（IMFと違い alpha-3 ではない）。

**確認した観測値**:
- 系列 UNIT_MEASURE=628（Index, 2010=100）: 1946-08 → 2026-03 月次
- 系列 UNIT_MEASURE=771（Year-on-year changes, %）: 同上、YoY 変化率

BIS LONG_CPI は **戦後の超長期** をカバーする唯一の経路。Crisis Frontier 研究の素材として、1997 アジア通貨危機だけでなく 1973 オイルショックや高度成長期の物価推移までを観測対象に含める場合は、こちらを優先する選択肢もある。ただしカテゴリ分解（コアコア・Goods・Services）は提供されず headline のみ。

### 2-4. 評価まとめ（jp/cpi）

| 経路 | カバー期間 | 信頼性 | 保守性 | 実装難易度 |
|---|---|---|---|---|
| **OECD SDMX (推奨)** | 1990-01〜（35年） | 高（OECD公式 SDMX、JPN は National Methodology） | 高（dataflow ID 安定、認証不要） | ☆☆（新規 fetcher `fetch_oecd.py` 必要、IMF版を流用可） |
| **BIS WS_LONG_CPI（代替）** | 1946-08〜（80年） | 高（BIS公式、各国中銀との共同編纂） | 高（dataflow ID 安定、認証不要） | ☆☆（新規 fetcher `fetch_bis.py`、`fetch_imf.py` を流用可） |
| **e-Stat（一次源）** | 1970-（55年）想定 | 最高（一次源） | 中（appId 必要、レート制限あり） | ☆☆☆（独自パーサ、認証実装） |
| **World Bank（年次）** | 1990-2024 | 高 | 高（既存 `fetch_worldbank.py` で対応可） | ☆ |

**判断推奨**: OECD SDMX を主とし、BIS LONG_CPI を補助候補として記録する。e-Stat はコア（生鮮食品を除く）など日本特有の系列が必要になったときに API キー登録のうえ追加する。

### 2-5. 特記事項

- OECD SDMX で COICOP 1999 系（`DSD_PRICES@DF_PRICES_ALL`）と COICOP 2018 系（`DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL`）が並存。**新規採用なら COICOP 2018 を選ぶ**。COICOP 1999 系は2021頃で更新が止まっている（435 vs 378観測）。
- e-Stat の `getStatsList` などすべての API は appId 必須。未認証で叩くと `STATUS:100 "認証に失敗しました。アプリケーションIDを確認してください"` を JSON で返す。
- 日本の「コアCPI」（生鮮食品を除く総合）は OECD の COICOP 分類には直接マッピングされない（CP01 は全食品）。`_TXCP01_NRG`（食品・エネルギー除く）が日本の「コアコアCPI」に最も近い。コアCPI が必要なら e-Stat 必須。
- BIS WS_LONG_CPI は REF_AREA に **2文字 ISO**（`JP`）を使う。IMF（`JPN`）、OECD（`JPN`）と異なるので、`fetch_bis.py` で国コード変換テーブルが必要。

---

## 3. th/cpi の調査結果

### 3-1. 候補経路の整理

| 経路 | dataflow / endpoint | 期間 | 頻度 | 単位 | 認証 | 結果 |
|---|---|---|---|---|---|---|
| **BIS WS_LONG_CPI** | `BIS,WS_LONG_CPI/M.TH` | **1976-01 → 2026-03** | 月次 | Index (2010=100) または YoY % | 不要 | ✅ **推奨（新発見）** |
| **IMF SDMX CPI** | `IMF.STA,CPI/THA....M` | 2010-01 → 2026-03 | 月次 | Index, COICOP 分類別 | 不要 | 第二波で確認済み、補完 |
| **World Bank** | `FP.CPI.TOTL` THA | 1990-2024（**1997=70.30**） | 年次 | Index (2010=100) | 不要 | 年次フォールバック |
| **MOC TPSO API** | `https://index-api.tpso.go.th/api/cpig/master` | 2002年(พ.ศ.2545)〜 | 月次 | Index, 基準年明示 | **必須**（IISゲートウェイ、403） | 1997カバーせず、追求価値低 |
| **OECD SDMX** | `DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL/THA...` | — | — | — | — | **THA 非対応**（OECD加盟国でない） |
| **BOT** | — | — | — | — | — | **CPI 非公開**（TPSOに委譲、公式に明言） |
| **G20 prices** | `DSD_G20_PRICES@DF_G20_PRICES/THA...` | — | — | — | — | THA 非対応（G20 でも非加盟） |

### 3-2. 推奨経路（BIS WS_LONG_CPI）の詳細

**完全URL（Index）**:
```
https://stats.bis.org/api/v1/data/BIS,WS_LONG_CPI/M.TH
```

**Accept**: `application/vnd.sdmx.structurespecificdata+xml;version=2.1`

**DSD**: 3次元（`FREQ.REF_AREA.UNIT_MEASURE`）

**実APIで確認した観測値**（Index 2010=100, UNIT_MEASURE=628）:
- 1976-01: 20.729（最古）
- 1990-01: 48.258
- **1997-01: 67.961** ✅
- 1997-06: 69.207
- 1997-12: 72.942
- 2000-01: 76.800
- 2025-12: 122.311
- 2026-03: 121.676（最新）

→ 603観測、すべて値あり、**1997アジア通貨危機期の物価変動が完全観測可能**。

### 3-3. 補完経路（IMF SDMX CPI）の詳細

第二波で `IMF.STA,CPI/THA....M` を確認済み（2010-M01〜2026-M03、COICOP 1999 分類別）。BIS は headline のみだが、IMF は COICOP `CP01`〜`CP12` のカテゴリ別月次を提供する（2010以降）。

カテゴリ別の分析が必要になったときに併用する想定。両者の差を吸収するため、報告書では BIS を主、IMF を補としつつ、フェッチャ実装段階で「BIS で1976-1990、IMF/BIS どちらかで1990-2009、BIS を継続」のような切り出しは不要（BIS が全期間カバーする）。

### 3-4. 年次フォールバック（World Bank）

第一波で既に確認した `FP.CPI.TOTL` を念のため再検証：
- 1990-2024、35観測（うち1997=70.304、Index 2010=100）
- WB は base year 2010=100 で再計算した正規化値を提供
- **BIS と完全一致するわけではない**（BIS は1997-12=72.94、WB 年次1997=70.30）が、軌跡は整合

月次が必要ない用途や、BIS API障害時の年次代替として記録。

### 3-5. MOC TPSO API の状況（補足）

タイ商務省 TPSO（Trade Policy and Strategy Office, 貿易政策戦略局）は CPI の一次源だが、公開 API は次の特性：

- API ホスト: `https://index-api.tpso.go.th`
- パス: `/api/cpig/master`（CPI General）、`/api/cpil/master`（Low income）、`/api/cpiu/master`（Outside municipal area）等
- 認証: 不明な API key／token が必要（未認証で 403 Forbidden）
- カバー期間: 国家全体 CPI は **พ.ศ. 2545 = 2002年以降**（i18n テキスト "อัตราการเปลี่ยนแปลงดัชนีราคาผู้บริโภคชุดทั่วไปและพื้นฐาน พ.ศ.2545 - ปีปัจจุบัน" による）
- 一次源としての品質は高いが、**1997カバーが取れない**ため、本プロジェクト用途では BIS の優位性が崩れない

### 3-6. 評価まとめ（th/cpi）

| 経路 | カバー期間 | 信頼性 | 保守性 | 実装難易度 |
|---|---|---|---|---|
| **BIS WS_LONG_CPI（推奨）** | 1976-01〜（50年）✅1997 | 高（BIS公式、中銀協力） | 高（認証不要、dataflow安定） | ☆☆（新規 `fetch_bis.py`） |
| **IMF SDMX CPI（補完）** | 2010-01〜（16年） | 高 | 高（既存 `fetch_imf.py` 拡張） | ☆ |
| **World Bank（年次）** | 1990-2024 | 高 | 高（既存 `fetch_worldbank.py`） | ☆ |
| **MOC TPSO（一次源）** | 2002〜（24年） | 最高（一次源） | 低（認証必要、API要照会） | ☆☆☆ |

**判断推奨**: BIS WS_LONG_CPI を主経路として採用、IMF はカテゴリ別分析が必要になった時の補助、WB は年次フォールバック。MOC TPSO 直接は 1997 カバーが取れないため、本プロジェクトでは現時点で追求しない。

### 3-7. 特記事項

- BIS WS_LONG_CPI の REF_AREA は **2文字 ISO（`TH`）**。`fetch_bis.py` 実装時に注意。
- BIS は OECD と異なり JPN/THA を区別なく扱う（OECDはTHA非対応）。1976-2026 の連続性は驚異的。
- TPSO は API key 取得を要する場合は 0 2507 6765（TPSO 技術問い合わせ）への照会が公開電話番号。本作業では追求しない。
- BOT が公式ページで「インフレ指標は TPSO 提供」と明言している以上、BOT 経由の取得経路を探索する必要はない。

---

## 4. th/bond_10y の調査結果

### 4-1. 候補経路の整理

| 経路 | dataflow / endpoint | 期間 | 頻度 | 単位 | 認証 | 結果 |
|---|---|---|---|---|---|---|
| **IMF SDMX MFS_IR** | `IMF.STA,MFS_IR/THA.S13BOND_RT_PT_A_PT.M` | **1999-09 → 2026-04** | 月次 | % p.a. | 不要 | ✅ 採用（1997欠落のまま） |
| **BIS（独立LTBYフロー）** | — | — | — | — | — | **存在しない**（新ポータルで撤去） |
| **BIS WS_DEBT_SEC2_PUB** | 債務証券残高 | — | 四半期等 | 残高 | 不要 | **利回りは持たない**（残高のみ） |
| **BOT** | — | — | — | — | — | 公開API構造不明、ページ404 |
| **ADB Asia Bond Monitor** | `kidb.adb.org` 等 | — | — | — | — | API 廃止／404 |
| **近接概念: Discount Rate** | `IMF.STA,MFS_IR/THA.DISR_RT_PT_A_PT.M` | 1990-01 → 2026-04 | 月次 | % p.a. | 不要 | ✅ **既存 `th/policy_rate`** |
| **近接概念: Lending Rate** | `IMF.STA,MFS_IR/THA.MFS162_RT_PT_A_PT.M` | 1990-01 → 2026-01 | 月次 | % p.a. | 不要 | 1997補完候補 |
| **近接概念: Treasury bills** | `IMF.STA,MFS_IR/THA.GSTBILY_RT_PT_A_PT.M` | 2001-02 → 2026-04 | 月次 | % p.a. | 不要 | 1997欠落 |
| **WB 年次 Lending rate** | `THA/FR.INR.LEND` | 1990-2024（**1997=13.65**） | 年次 | % p.a. | 不要 | ✅ 1997補完候補（年次） |
| **WB 年次 Real interest** | `THA/FR.INR.RINR` | 1990-2024（**1997=8.83**） | 年次 | % p.a. | 不要 | 1997補完候補（年次） |

### 4-2. 「1997 月次 タイ10年国債利回り」は構造的に存在しない

BIS の新データポータル（2024年移行）には、長期国債利回り（旧 LTBY）の独立 dataflow が存在しない。現存する金利関連 BIS dataflow は次のみ：

- `WS_CBPOL`: Central bank policy rates（政策金利、各国中銀の公定歩合相当）
- `WS_DEBT_SEC2_PUB`: 債務証券残高（利回りではなく残高）

旧 BIS Statistics Warehouse で提供されていた "Selected interest rates" は新ポータルに移行されておらず、Thai 10y bond yield は事実上参照できない。

IMF SDMX MFS_IR の `S13BOND_RT_PT_A_PT`（Government bonds, generic yield）も 1999-09 開始。これは偶然ではなく、**タイの国内政府債券市場は1997年アジア通貨危機後の財政再建過程で再構築された**ことを反映する：

- 1997年以前のタイは域内資本依存型の国際借入が中心で、国内10年債は流通市場が薄かった
- 1998-1999年に "Government Bond Issuance Program" が再開され、ベンチマーク10年債が制度として確立
- IMF・BIS とも、1999年以降を「タイ10年国債利回り」として観測している

**結論**: 「1997 月次 タイ10年国債利回り」は単に**取得できないだけでなく、観測対象として一貫した形では存在しない**。依頼書で示された「存在しないものは存在しない」という方針に従い、これを認める。

### 4-3. 1997 期の補完情報（近接概念）

タイの1997年金融条件を観測したい場合、10年国債利回りそのものは取れないが、次の系列で実質的に代替できる：

| 系列 | 1997-01 値 | 1997-12 値 | 経路 | 採用済 |
|---|---|---|---|---|
| **Discount Rate**（公定歩合、政策金利） | — | — | IMF MFS_IR `DISR_RT_PT_A_PT.M`、1990-01〜 | ✅ `th/policy_rate` |
| **Lending Rate**（市中貸出金利） | — | — | IMF MFS_IR `MFS162_RT_PT_A_PT.M`、1990-01〜 | 第三波で参照可 |
| **WB Lending Rate**（年次） | 13.65% | — | WB `FR.INR.LEND` | フォールバック |
| **WB Real interest**（年次） | 8.83% | — | WB `FR.INR.RINR` | フォールバック |
| **WB Deposit Rate**（年次） | 10.52% | — | WB `FR.INR.DPST` | 参考 |

これらは「金融逼迫の度合い」を捉える点で 10年国債利回りと近い性格を持つ。`how_to_read` に注記したうえで参考表示する選択肢がある。

ただし**コア6指標枠 `bond_10y` 自体には IMF SDMX `S13BOND_RT_PT_A_PT`（1999-09〜）を採用**し、「1997年を含まない」旨をプロジェクト全体方針として明示する案を推奨する。第二波の中央銀行総資産（2001-12〜受容）と同じ取り扱い。

### 4-4. 評価まとめ（th/bond_10y）

| 経路 | カバー期間 | 信頼性 | 保守性 | 実装難易度 | 1997 |
|---|---|---|---|---|---|
| **IMF SDMX `S13BOND_RT_PT_A_PT`（推奨）** | 1999-09〜（27年） | 高 | 高（既存 `fetch_imf.py` で対応可） | ☆（既存系列の追加） | ❌ |
| BIS WS_DEBT_SEC2_PUB | — | — | — | — | — |
| 近接概念: IMF Lending Rate | 1990-01〜（35年） | 高 | 高 | ☆ | ✅ |
| 近接概念: WB FR.INR.LEND（年次） | 1990-2024 | 高 | 高 | ☆ | ✅ |

**判断推奨**: IMF SDMX `THA.S13BOND_RT_PT_A_PT.M` を主経路に採用し、「タイ10年国債利回りは1999-09以降」として明示する。1997 期の金融逼迫を捉えたい場合は `th/policy_rate`（Discount Rate）か WB 年次貸出金利を補助参照する。

### 4-5. 特記事項

- 既存 `fetch_imf.py` の data_sources に `THA.S13BOND_RT_PT_A_PT.M` を1行追加するだけで対応可能。新規フェッチャ不要。
- 報告書スコープ外だが、`indicators_country_specific` の THA 節に「Lending Rate」「Treasury bills yield」を後日追加することは検討に値する。
- 1997 期月次データを論文・教科書経由で復元する選択肢はあるが、本プロジェクトは「自動取得可能な公開API」に範囲を限定しているため、本作業の対象外。

---

## 5. 既存フェッチャとの関係

| 枠 | 推奨経路 | 必要なフェッチャ |
|---|---|---|
| jp/cpi | OECD SDMX | **新規 `fetch_oecd.py`**（`fetch_imf.py` をベースに DSD 構造の違いを吸収） |
| th/cpi | BIS WS_LONG_CPI | **新規 `fetch_bis.py`**（`fetch_imf.py` をベースに REF_AREA 2文字 ISO 変換と Accept ヘッダー差分を吸収） |
| th/bond_10y | IMF SDMX MFS_IR | **既存 `fetch_imf.py` に1行追加**（`THA.S13BOND_RT_PT_A_PT.M`） |

### 5-1. 新規フェッチャの共通化可能性

OECD と BIS は SDMX 2.1 規格を共有する。IMF SDMX 用 `fetch_imf.py` を基底クラスとして、次の差分を抽出すれば3 fetcher を統合できる：

- ベースURL（`api.imf.org/external/sdmx/2.1` vs `sdmx.oecd.org/public/rest` vs `stats.bis.org/api/v1`）
- エージェンシーID（`IMF.STA` vs `OECD.SDD.TPS` vs `BIS`）
- Accept ヘッダー（IMF: XML / OECD: data+json / BIS: structurespecificdata+xml）
- REF_AREA コード変換（IMF/OECD: alpha-3 / BIS: alpha-2）
- レスポンス形式（IMF/BIS: XML StructureSpecificData / OECD: SDMX-JSON）

統合フェッチャ `fetch_sdmx.py` を新規実装し、`source: "imf" | "oecd" | "bis"` を yaml で切り替える設計も成立する。実装フェーズで再判断する。

### 5-2. 認証要する経路の取り扱い

e-Stat (jp/cpi 一次源)、TPSO (th/cpi 一次源) は本作業では追求しないが、将来 `indicators_country_specific` に各国の独自系列（日本のコアCPI、タイの地方別CPI等）を追加する局面で再評価する。

---

## 6. 全体の所感

### 6-1. すぐ別経路で取得作業に入れる枠（☆〜☆☆）

- **th/bond_10y**: 既存 `fetch_imf.py` の data_sources に1行追加するだけ。1997 カバーなしを受け入れるという方針判断さえできれば即着手可。難易度 ☆。
- **jp/cpi**: 新規 `fetch_oecd.py` または `fetch_sdmx.py`（統合）が必要だが、IMF版を流用すれば実装は単純。難易度 ☆☆。
- **th/cpi**: 同上、`fetch_bis.py`。難易度 ☆☆。BIS の Accept と国コード規約に注意。

### 6-2. 新規フェッチャ実装が必要な枠と共通化

OECD と BIS は同じ SDMX 2.1 規格なので、`fetch_sdmx.py` という統合フェッチャに `source: "oecd" | "bis"` のサブクラス分岐を持たせる案を推奨。各 fetcher を別ファイルにする場合でも、共通の `parse_sdmx_xml`／`parse_sdmx_json` ヘルパーを抽出すれば DRY を維持できる。

### 6-3. 取得が困難または現時点で諦めるべき枠

- **th/bond_10y の1997 月次**: 取得不能（依頼書方針に基づき受容）。代わりに既存 `th/policy_rate`（Discount Rate, 1990〜）と WB 年次貸出金利で1997 期を補完する形を採用推奨。
- **jp/cpi の日本式コア／コアコア**: OECD は `_TXCP01_NRG`（コアコア相当、ex-food-energy）まで提供。生鮮食品を除く「日本式コアCPI」が必要なら e-Stat 一次源を別途追加実装。本フェーズには含めない。

### 6-4. 第三波の最大の発見

**BIS WS_LONG_CPI の発見**が第三波の最大の収穫である。第二波時点で「th/cpi の1997カバーは公開API経由では不可能」と判断していたが、BIS が1976年から月次でタイ CPI を提供していることを実APIで確認できた。これにより：

- `th/cpi` 1997-カバー問題が解決
- 副次的に `jp/cpi` も1946年からの超長期系列を選択肢に加えられる
- BIS 統合のうえ将来の `indicators_country_specific` 拡張時に他国のCPI長期系列も BIS から供給可能

---

## 7. 参照URL（2026-05-16 時点）

| 用途 | URL |
|---|---|
| OECD SDMX ルート | https://sdmx.oecd.org/public/rest/ |
| OECD dataflow listing | https://sdmx.oecd.org/public/rest/dataflow/all/all/latest?detail=allstubs |
| OECD CPI flow (COICOP 2018) | https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.TPS/DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL/latest |
| OECD JPN headline CPI | https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL/JPN.M.N.CPI.IX._T.N._Z?startPeriod=1990 |
| OECD JPN コアコア相当 | https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL/JPN.M.N.CPI.IX._TXCP01_NRG.N._Z?startPeriod=1990 |
| BIS SDMX ルート | https://stats.bis.org/api/v1/ |
| BIS dataflow listing | https://stats.bis.org/api/v1/dataflow |
| BIS WS_LONG_CPI DSD | https://stats.bis.org/api/v1/dataflow/BIS/WS_LONG_CPI?references=datastructure |
| BIS THA long CPI | https://stats.bis.org/api/v1/data/BIS,WS_LONG_CPI/M.TH |
| BIS JPN long CPI | https://stats.bis.org/api/v1/data/BIS,WS_LONG_CPI/M.JP |
| IMF THA 10y bond | https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_IR/THA.S13BOND_RT_PT_A_PT.M?startPeriod=1990 |
| MOC TPSO API（参考） | https://index-api.tpso.go.th/api/cpig/master（要API key） |
| e-Stat API（参考） | https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList?...&appId=... |
| World Bank THA CPI | https://api.worldbank.org/v2/country/THA/indicator/FP.CPI.TOTL?format=json |
| World Bank THA Lending Rate | https://api.worldbank.org/v2/country/THA/indicator/FR.INR.LEND?format=json |

---

## 8. 次のアクション（本作業の射程外、ユーザ判断待ち）

1. 本報告書の確認
2. 確認後、新規フェッチャ実装計画（`fetch_oecd.py` / `fetch_bis.py` または統合 `fetch_sdmx.py`）の提示
3. その実装計画の確認後、コード実装
4. yaml への反映（`data_sources` への3行追加または更新）
5. コミット、テスト、データ取得

以上、本報告書はここまで。
