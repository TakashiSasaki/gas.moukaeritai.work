# Housekeeping: by-apps-script-api

このディレクトリは、Google Apps Script API を直接使用して取得した生の情報を管理します。

## ツール

### `fetch_apps_script_info.py`
Google Apps Script API (`v1/projects`) を使用して、所有しているプロジェクトの一覧を取得し、JSON 形式で保存します。

#### 特徴
- **OAuth2 認証**: `~/.clasprc.json` に保存されている `clasp` の認証情報を利用します。
- **トークンの自動更新**: アクセストークンが切れている場合、リフレッシュトークンを使用して自動的に更新します。
- **履歴管理**: 実行時のタイムスタンプをファイル名（`YYYYMMDD-HHMMSS.json`）として保存します。
- **自動削除**: ディレクトリ内に 6 件以上の JSON ファイルが存在する場合、古いものから順に削除し、直近 5 件のみを維持します。

#### 使用方法
このスクリプトは `requests` ライブラリに依存しています。`uv` を使用して以下のように実行することを推奨します：

```bash
uv run --with requests housekeeping/by-apps-script-api/fetch_apps_script_info.py
```

## 運用ルール
1. **API 利用の健全性**: `clasp list` プロセスを介さず直接 API を叩くため、より詳細な情報取得や自動化に適しています。
2. **依存関係の管理**: ライブラリの依存関係を最小限に抑えるため、`uv run` による動的な実行を前提としています。
