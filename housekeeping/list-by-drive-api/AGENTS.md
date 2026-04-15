# Housekeeping: list-by-drive-api

このディレクトリは、Google Drive API v3 から取得した Google Apps Script プロジェクト一覧の生データと、その結果をローカル管理用メタデータへ反映するスクリプトを管理します。

## 目的

- `clasp list` に依存せず、Drive API から Apps Script プロジェクト一覧を直接取得する
- 取得結果をタイムスタンプ付き JSON として履歴保存する
- 最新バックアップをもとに `projects/<SCRIPT_ID>/metadata.json` を更新する
- 必要に応じて不足している project ディレクトリや `.clasp.json` を補完する
- Web 用の `docs/projects.json` を再生成する

## ファイル構成

### `fetch-list.py`
Google Drive API v3 を使って、所有している Apps Script プロジェクトの一覧を全件取得し、このディレクトリに `YYYYMMDD-HHMMSS.json` 形式で保存します。

#### 現在の挙動
- `~/.clasprc.json` から `clasp` の OAuth 情報を読む
- `token` 形式と `tokens.default` 形式の両方に対応する
- リフレッシュトークンを使ってアクセストークンを都度更新する
- `mimeType = 'application/vnd.google-apps.script' and trashed = false` の条件で Drive API を検索する
- `id`, `name`, `createdTime`, `modifiedTime` を取得する
- ページネーションを辿って全件取得する
- 保存後、このディレクトリ内のタイムスタンプ付き JSON を新しいもの 5 件だけ残して古いものを削除する

#### 実行方法
`requests` が必要です。`uv` 経由の実行を前提にしてください。

```bash
uv run --with requests housekeeping/list-by-drive-api/fetch-list.py
```

### `update_metadata.py`
最新のバックアップ JSON を読み込み、各 project ディレクトリの `metadata.json` を更新します。

#### 現在の挙動
- デフォルトではこのディレクトリ内の最新 `YYYYMMDD-HHMMSS.json` を読む
- デフォルトではリポジトリ直下の `projects/` を更新対象にする
- `projects/<SCRIPT_ID>/` が存在しなければ自動作成する
- `.clasp.json` が無ければ `{"scriptId": "<SCRIPT_ID>"}` を作成する
- `metadata.json` の `driveApi` ブロックに以下を保存する
  - `id`
  - `name`
  - `createdTime`
  - `modifiedTime`
- 旧形式のルート直下プロパティを整理する
  - `id`, `url`
  - `name`, `createdTime`, `modifiedTime`, `lastUpdated`
  - `titleByClaspList`, `titleByDriveApi`
  - `application.json`, `deployments.json`, `versions.json`
- `deployments.json` と `versions.json` が project ディレクトリに残っていれば `metadata.json` に取り込み、その後ファイルを削除する
- あわせて `deployments.txt`, `versions.txt` も削除対象にする
- 最後に `docs/projects.json` を再生成する
  - 各 project の `id` と `name` を出力する
  - 名前は `metadata.json` の `driveApi.name` を優先し、無ければ `appsScriptApi.title` を使う
  - 名前でソートして保存する

#### 実行方法

```bash
uv run python housekeeping/list-by-drive-api/update_metadata.py
```

#### オプション

```bash
uv run python housekeeping/list-by-drive-api/update_metadata.py --dir housekeeping/list-by-drive-api --projects projects
```

- `--dir` (`-d`): バックアップ JSON が置かれているディレクトリ
- `--projects` (`-p`): 更新対象の `projects/` ディレクトリ

## エージェント向け運用ルール

1. `fetch-list.py` を変更する場合は、`~/.clasprc.json` の 2 つの構造 (`token` / `tokens.default`) の互換性を壊さないこと。
2. バックアップ JSON は履歴ファイルです。既存の `YYYYMMDD-HHMMSS.json` を手で編集しないこと。
3. `update_metadata.py` は `metadata.json` 更新だけでなく、project ディレクトリ補完、`.clasp.json` 作成、旧ファイルの移行、`docs/projects.json` 再生成まで担当しています。変更時はこの一連の責務を崩さないこと。
4. `docs/projects.json` は生成物です。手編集せず、必要なら `update_metadata.py` を実行して更新すること。
5. `projects/` 配下の構造はリポジトリ全体のルールに従い、`projects/<SCRIPT_ID>/` を維持すること。
6. 新しい metadata フィールドを追加する場合は、既存の `driveApi` / `appsScriptApi` 構造との整合性を確認すること。
7. エラー処理を変える場合は、認証失敗、API 失敗、JSON 読み書き失敗、欠損ファイルのケースを明示的に考慮すること。

## よくある作業

### 最新一覧を取得する

```bash
uv run --with requests housekeeping/list-by-drive-api/fetch-list.py
```

### 最新バックアップを project metadata に反映する

```bash
uv run python housekeeping/list-by-drive-api/update_metadata.py
```

### 別ディレクトリを対象に metadata を更新する

```bash
uv run python housekeeping/list-by-drive-api/update_metadata.py -d housekeeping/list-by-drive-api -p projects
```
