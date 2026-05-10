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
