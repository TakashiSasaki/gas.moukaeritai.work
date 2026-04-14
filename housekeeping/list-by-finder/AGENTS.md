# Housekeeping: list-by-finder

このディレクトリは、Google Apps Script Web App (GAS Project Finder) から取得した情報を管理します。

## ツール

### `fetch.py`
GAS Project Finder の Web App URL (`.../exec?json`) からプロジェクト情報の JSON データを取得し、ファイルとして保存します。
これは既存のワークフロー (`b1-gas-project-finder.yml`) で使用されていた `curl` コマンドの機能を代替・拡張するものです。

#### 特徴
- **リダイレクト対応**: GAS Web App 特有のリダイレクトを自動的に処理します。
- **履歴管理**: 実行時のタイムスタンプをファイル名（`YYYYMMDD-HHMMSS.json`）として保存します。
- **自動削除**: ディレクトリ内に 6 件以上の JSON ファイルが存在する場合、古いものから順に削除し、直近 5 件のみを維持します。

#### 使用方法
このスクリプトは `requests` ライブラリに依存しています。`uv` を使用して以下のように実行することを推奨します：

```bash
uv run --with requests housekeeping/list-by-finder/fetch.py
```

## 運用ルール
1. **履歴の保持**: 保存された JSON ファイルは、Finder 自体のデータが更新された際の履歴として機能します。
2. **依存関係の管理**: ライブラリの依存関係を最小限に抑えるため、`uv run` による動的な実行を前提としています。
