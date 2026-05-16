# プロジェクトTODO

## 2026-05-28 までに削除予定

- `data/crisis_frontier.db.20260428_backup`
  - フェーズ2 着手時、DB スキーマ刷新（country_id 大文字→小文字、`reserves` → `fx_reserves` rename）に伴って取得した一回限りのバックアップ。
  - 新スキーマで `python run_all.py` が正常に完走することは 2026-04-28 に確認済み。
  - 1ヶ月（2026-05-28 以降）この削除タスクが残っていれば、安全に削除してよい。
  - 削除コマンド：`rm data/crisis_frontier.db.20260428_backup`

## (C) 国別補足注記のスキーマ拡張

第一波（2026-05-09）の動作確認で、indicators_global.fx_reserves.how_to_read および
indicators_global.central_bank_total_assets.source_note に追記した米国補足が、
JP/TH の国別ページにも表示される問題が判明。本文で「米国は…」と明示しているため
事実誤認は起きないが、文脈ミスマッチが生じる。

解決策：yaml スキーマに how_to_read_country_specific: { us: "..." } のような
国別補足フィールドを追加し、export_html.py の render_indicator_card 関数を
country_id 引数で出し分ける形に改修する。

優先度：中（第一波・第二波が落ち着いてから整備フェーズで対応）

## (D) run_all.py の subprocess エンコーディング不整合

run_all.py の `subprocess.run(..., encoding="cp932")` と、フェッチャ側の日本語 print
出力（実体は UTF-8）が不整合で、`UnicodeDecodeError: 'cp932' codec can't decode ...`
が各 STEP のログに出る。各 STEP の return code は 0 で動作には影響しないが、
フェッチャの `"{n}件保存"` メッセージがログに記録されない。

解決策：`encoding="cp932"` を `encoding="utf-8", errors="replace"` に変更する。
Anaconda 環境・venv 環境とも標準で UTF-8 出力に揃えられているため、cp932 を
維持する積極的理由はない。

優先度：低（観察事項。動作には影響なし。デバッグログ整備時にまとめて対応）

## (E) export_html.py の source 表示マッピングに imf/oecd/bis を追加

各指標カードの「出典:」メタ行で、`fred` は `FRED`、`worldbank` は `World Bank` と
整形表示されるが、`imf` / `oecd` / `bis` は小文字のまま表示される
（例：`出典: imf (MFS_CBS/...)`）。第二波の IMF 統合時から存在する既存挙動。

解決策：export_html.py の source 表示マッピング辞書に次を追加：
- imf → "IMF SDMX"
- oecd → "OECD SDMX"
- bis → "BIS SDMX"

優先度：低（表記の整合性向上のみ。データの正確性には影響なし）
