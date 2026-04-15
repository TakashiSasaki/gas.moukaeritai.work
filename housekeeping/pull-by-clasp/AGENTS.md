# Housekeeping: pull-by-clasp

このディレクトリは、リポジトリ内の Google Apps Script project を `clasp` で pull しつつ、Apps Script API 由来の補助メタデータを `metadata.json` に統合して更新するためのスクリプトを管理します。

## 目的

- `projects/` 配下、または実行ディレクトリ直下にある `.clasp.json` 付き project ディレクトリを列挙する
- 各 project について、必要な場合のみ `clasp pull` を実行する
- `clasp deployments` と `clasp versions` の結果を取得して `metadata.json` に統合する
- Apps Script API から project 本体メタデータと file 一覧メタデータを取得して `metadata.json` に統合する
- 旧来の standalone な補助ファイルを整理し、project ごとのメタデータを一元化する

## ファイル構成

### `clasp-pull.py`
全 project を走査して、必要なら `clasp pull` を実行し、関連するメタデータも更新します。

#### 現在の挙動
- カレントディレクトリ基準で `projects/` を優先して探索する
- `projects/` があればその直下、加えて実行ディレクトリ直下も探索する
- `.clasp.json` を持つディレクトリだけを対象にする
- 同じ実体パスは 1 回だけ処理する
- 実行開始時に `clasp -v` を試し、その後 `clasp list` を 1 回実行してトークン更新を促す
- `~/.clasprc.json` から access token を読み取る
  - `token.access_token`
  - ルート直下の `access_token`
  - `tokens.*.access_token`
  の順で拾える構造に対応する
- access token が読める場合、Apps Script API の `projects.get` を使って remote の `updateTime` を取得する
- local の `metadata.json` にある `appsScriptApi.updateTime` または旧 `lastUpdated` と比較し、更新不要なら `clasp pull` をスキップする
- pull が必要な場合は以下を順に行う
  - `clasp pull`
  - `clasp deployments`
  - `clasp versions`
  - Apps Script API `/content` による file 一覧取得
  - `metadata.json` の更新
  - 旧 standalone ファイルの削除
- `clasp` コマンド失敗時は最大 3 回まで再試行する
  - 各 retry 前に `clasp list` を試してトークン再取得を促す
- Apps Script API `/content` から取得した file 名に大文字小文字だけ異なる衝突がある場合、Windows での path 衝突を防ぐため即座に終了する

## `metadata.json` の更新内容

`clasp-pull.py` は project ごとの `metadata.json` に以下を統合します。

- `appsScriptApi`
  - Apps Script API `projects.get` の応答全体を保存する
- `deployments`
  - `clasp deployments` の結果を整形して保存する
- `versions`
  - `clasp versions` の結果を整形して保存する
- `files`
  - Apps Script API `/content` の file 一覧から、source code と `functionSet` を除いた情報を保存する

同時に、以下の旧 root プロパティは削除対象です。

- `lastUpdated`
- `name`
- `createdTime`
- `modifiedTime`
- `titleByClaspList`
- `titleByDriveApi`
- `application.json`
- `deployments.json`
- `versions.json`

また、以下の standalone ファイルが残っていれば削除します。

- `deployments.json`
- `deployments.txt`
- `versions.json`
- `versions.txt`

## 実行方法

通常はリポジトリ root から実行してください。

```bash
uv run python housekeeping/pull-by-clasp/clasp-pull.py
```

`uv` を使わずに Python から直接実行しても動きますが、`clasp` CLI が別途利用可能であることが前提です。

## 前提条件

- `clasp` がインストールされていて、シェルから `clasp` コマンドを実行できること
- `~/.clasprc.json` に有効な認証情報があること
- ネットワーク越しに以下へアクセスできること
  - `clasp` が利用する Google APIs
  - `https://script.googleapis.com/v1/projects/...`
- 各 project ディレクトリに `.clasp.json` が存在すること

## エージェント向け運用ルール

1. このスクリプトは単なる `clasp pull` ラッパーではありません。差分判定、Apps Script API 取得、`metadata.json` 統合更新、旧ファイル cleanup までが責務です。変更時にこの流れを崩さないこと。
2. project 走査ロジックは `projects/` 直下優先ですが、実行ディレクトリ直下も見る実装です。探索範囲を狭める変更は、既存運用への影響を確認してから行うこと。
3. `.clasprc.json` の token 構造には複数互換があります。認証まわりを変更する場合は既存の読み取り互換性を保つこと。
4. Windows では file 名の大文字小文字衝突が致命的です。`check_case_insensitive_name_conflicts` 相当の保護は削除しないこと。
5. `metadata.json` は他の housekeeping スクリプトとも連携します。`appsScriptApi`、`driveApi`、`deployments`、`versions`、`files` の構造を変更する場合は、関連スクリプトとの整合性を確認すること。
6. `deployments.json` や `versions.json` は生成物ではなく旧形式の残骸として cleanup 対象です。新しく復活させないこと。
7. エラー処理を変更する場合は、`clasp` 失敗時、API 失敗時、認証切れ時、破損した `metadata.json` 読み込み時の挙動を明示的に考慮すること。
8. 大量 project を処理する前提なので、追加の API 呼び出しや filesystem 走査を増やす変更はコストを意識すること。

## よくある作業

### 全 project を pull して metadata を更新する

```bash
uv run python housekeeping/pull-by-clasp/clasp-pull.py
```

### 単体 project だけを試したい場合

このスクリプト自体には単体 project 指定オプションはありません。必要なら対象 project を含むディレクトリをカレントにして実行範囲を調整するか、別の補助スクリプトを使ってください。

## 既知の注意点

- `clasp list` は token refresh のために使われています。認証切れ時に完全には回復しないこともあるため、必要なら `clasp login` などの再認証が必要です。
- Apps Script API から remote metadata を取得できない場合は、差分判定の最適化をあきらめて pull 側へ倒れることがあります。
- `clasp` の出力形式が変わると `deployments` / `versions` の parser が影響を受けます。CLI 更新時は必要に応じて追従してください。
