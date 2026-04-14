# Housekeeping: list-by-drive-api

このディレクトリは、Google Drive API v3 を直接使用して取得した生の情報を管理します。

## ツール

### `fetch.py`
Google Drive API v3 を使用して、所有している Google Apps Script プロジェクトの一覧を全件取得し、JSON 形式で保存します。

#### 特徴
- **OAuth2 認証**: `~/.clasprc.json` に保存されている `clasp` の認証情報を利用します。
- **トークンの自動更新**: アクセストークンが切れている場合、リフレッシュトークンを使用して自動的に更新します。
- **全件取得（ページネーション）**: `nextPageToken` を解釈し、100件を超えるプロジェクトがある場合でも全ページを自動的に取得します。
- **履歴管理**: 実行時のタイムスタンプをファイル名（`YYYYMMDD-HHMMSS.json`）として保存します。
- **自動削除**: ディレクトリ内に 6 件以上の JSON ファイルが存在する場合、古いものから順に削除し、直近 5 件のみを維持します。

#### 使用方法
このスクリプトは `requests` ライブラリに依存しています。`uv` を使用して以下のように実行することを推奨します：

```bash
uv run --with requests housekeeping/list-by-drive-api/fetch.py
```

### `update_metadata.py`
最新の JSON バックアップファイルからプロジェクト名（タイトル）を抽出し、各プロジェクトの `metadata.json` を更新します。

#### 特徴
- 各プロジェクトのフォルダ内にある `metadata.json` に **`"titleByDriveApi"`** プロパティを追加または更新します。
- これにより、Drive API から得られた最新のプロジェクト名を各プロジェクトのメタデータに同期できます。

#### 使用方法
```bash
uv run python housekeeping/list-by-drive-api/update_metadata.py
```

## 運用ルール
1. **API 利用の健全性**: `clasp list` プロセスを介さず直接 API を叩くため、より詳細な情報取得や自動化に適しています。
2. **メタデータの同期**: プロジェクト名の変更があった場合などは `update_metadata.py` を実行し、ローカルのメタデータに反映させます。
3. **依存関係の管理**: ライブラリが必要な場合は、`uv run` による動的な実行を前提とします。
