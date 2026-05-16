# プロジェクトTODO

## 2026-05-28 までに削除予定

- `data/crisis_frontier.db.20260428_backup`
  - フェーズ2 着手時、DB スキーマ刷新（country_id 大文字→小文字、`reserves` → `fx_reserves` rename）に伴って取得した一回限りのバックアップ。
  - 新スキーマで `python run_all.py` が正常に完走することは 2026-04-28 に確認済み。
  - 1ヶ月（2026-05-28 以降）この削除タスクが残っていれば、安全に削除してよい。
  - 削除コマンド：`rm data/crisis_frontier.db.20260428_backup`

