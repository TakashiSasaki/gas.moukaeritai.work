# Housekeeping: by-clasp-list

このディレクトリは、Google Apps Script プロジェクトの一覧（`clasp list`）の履歴を管理し、リポジトリの状態を維持するためのツールとデータを格納します。

## ツール

### `save_clasp_list.py`
`clasp list --noShorten` の生出力をテキストファイルとして保存します。

#### 使用方法
```bash
python housekeeping/by-clasp-list/save_clasp_list.py [オプション]
```

#### オプション
- `-o`, `--output PATH`: 
    - 保存先のファイルパスまたはディレクトリを指定します。
    - ディレクトリを指定した場合、`YYYYMMDD-HHMMSS.txt` という形式で保存されます。
    - デフォルト: スクリプトと同じディレクトリ。
- `-k`, `--keep N`:
    - 保持するバックアップファイルの件数を指定します。
    - 保存後、ディレクトリ内に `YYYYMMDD-HHMMSS.txt` 形式のファイルが $N$ 個より多く存在する場合、古いものから順に削除されます。
    - デフォルト: 5件。

### `test_clasp_list.py`
最新のバックアップファイルからプロジェクト ID を抽出し、`projects/` ディレクトリに実体が存在するかを確認します。

#### 使用方法
```bash
python housekeeping/by-clasp-list/test_clasp_list.py [オプション]
```

#### オプション
- `-d`, `--dir PATH`:
    - バックアップファイル（`.txt`）を探すディレクトリを指定します。
    - デフォルト: スクリプトと同じディレクトリ。

#### 特徴
- 指定されたディレクトリ内の最新の `YYYYMMDD-HHMMSS.txt` を自動認識します。
- URL からパスの一部（ID）を取り出し、ローカルの `projects/` フォルダと突き合わせます。
- 欠落しているプロジェクトや、逆にリポジトリにのみ存在する（clasp list にない）フォルダを報告します。

### `update_metadata_titles.py`
最新のバックアップファイルからプロジェクト名（タイトル）を抽出し、各プロジェクトの `metadata.json` を更新します。

#### 使用方法
```bash
python housekeeping/by-clasp-list/update_metadata_titles.py [オプション]
```

#### オプション
- `-d`, `--dir PATH`:
    - バックアップファイル（`.txt`）を探すディレクトリを指定します。
    - デフォルト: スクリプトと同じディレクトリ。

#### 特徴
- 各プロジェクトのフォルダ内にある `metadata.json` に `"titleByClaspList"` プロパティを追加または更新します。
- これにより、`clasp list` から得られた最新のプロジェクト名を各プロジェクトのメタデータに同期できます。

## 運用ルール
1. **定期的なバックアップ**: ワークフロー等で定期的に実行し、プロジェクトリストの変遷を記録します。
2. **自動整理**: `save_clasp_list.py` の `-k` オプションにより、不要な古いバックアップが自動的に削除されるため、手動での削除は通常不要です。
3. **整合性の検証**: 新しいプロジェクトを追加した後や定期メンテナンス時に `test_clasp_list.py` を実行し、リポジトリ内のディレクトリ構成と最新のプロジェクトリストに齟齬がないか確認します。
4. **メタデータの同期**: プロジェクト名の変更があった場合などは `update_metadata_titles.py` を実行し、ローカルのメタデータに反映させます。
