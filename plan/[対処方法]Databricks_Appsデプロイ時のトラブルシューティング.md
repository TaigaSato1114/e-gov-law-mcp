# Databricks Apps デプロイ時のトラブルシューティング

## 2026-07-06 発生した問題と解決策

### 根本原因

`uv` が `pyproject.toml` の `requires-python = ">=3.12"` を解釈し、コンテナ内で **Python 3.14 をダウンロードして使用**した。  
`pydantic-core` に Python 3.14 用のビルド済みホイール（wheel）が存在せず、ソースからの Rust ビルドも PyO3 の 3.14 非対応により失敗。

### エラーログ（抜粋）

```
Python reports SOABI: cpython-314-x86_64-linux-gnu
error: the configured Python interpreter version (3.14) is newer than
PyO3's maximum supported version (3.13)
```

### 解決策

`.python-version` ファイルをリポジトリルートに配置し、`uv` が使用する Python バージョンを固定した。

```
3.12
```

また `uv.lock` も `--python 3.12` オプション付きで再生成した。

---

## 今後の障害発生時の確認手順

### 1. Apps UI の Logs タブを確認

- ソースフィルタ: **APP** を選択
- スタックトレース全文をコピーする

### 2. ログ内のキーワードから原因を分類

| キーワード | 意味 | 対処 |
|---|---|---|
| `ImportError` / `ModuleNotFoundError` | パッケージ間のバージョン不整合 | `uv.lock` を再生成 (`uv lock --python 3.12`) |
| `maturin failed` / `cargo` / `pyo3` | Python バージョン用ホイールが無い | `.python-version` を確認、`requires-python` の上限を確認 |
| `TypeError: cannot specify both default and default_factory` | pydantic バージョン非互換 | pydantic のバージョン制約を調整 |
| `502 Bad Gateway` / `App Not Available` | アプリプロセスが起動していない | 上記いずれかの起動エラーが原因。Logs タブで APP ログを確認 |

### 3. アシスタントに提供すると診断が早い情報

1. **APP ソースのエラーログ**（スタックトレース全文）
2. `app.yaml` の内容
3. `pyproject.toml` の `dependencies` と `requires-python`
4. `.python-version` ファイルの有無と内容
5. `uv.lock` の主要パッケージバージョン（`grep -E '^(name|version)' uv.lock | grep -B1 'pydantic\|fastmcp\|mcp'`）

---

## 予防策

1. **`.python-version` ファイルを常にリポジトリに含める**
   - `uv` の Python 自動ダウンロード（最新版取得）を防止する
   - Databricks Apps コンテナは Python 3.12 をサポート

2. **`uv.lock` はデプロイ前に正しい Python バージョンで生成する**
   ```bash
   uv lock --python 3.12
   ```

3. **ワークスペースに `.venv` を作らない**
   - `uv sync` を実行するとシンボリックリンクを含む `.venv` が作成される
   - Databricks Apps のデプロイは `.venv` 内のシンボリックリンクをエクスポートできない（`type=symlink` エラー）
   - ロックファイルの生成のみ必要な場合は `uv lock` を使う

4. **`fastmcp` のバージョン制約**
   - `fastmcp>=2.8.1,<3.0.0` — 3.x は `typing_extensions.Sentinel` 問題あり
   - `pydantic` の上限ピンは不要（`.python-version` で 3.12 固定すれば互換ホイールが存在する）

---

## 現在の構成（正常動作確認済み）

| ファイル | 内容 |
|---|---|
| `.python-version` | `3.12` |
| `pyproject.toml` | `requires-python = ">=3.12"`, `fastmcp>=2.8.1,<3.0.0` |
| `app.yaml` | `sh -c` で環境変数設定 + `uv run e-gov-law-mcp --transport streamable-http` |
| `uv.lock` | `fastmcp==2.14.7`, `pydantic==2.13.4`, `pydantic-core==2.46.4` |

### app.yaml の環境変数

```yaml
command:
  - sh
  - -c
  - FASTMCP_JSON_RESPONSE=true FASTMCP_STATELESS_HTTP=true FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=false uv run e-gov-law-mcp --transport streamable-http
```

- `FASTMCP_JSON_RESPONSE=true` — SSE ではなく JSON レスポンスを返す（Playground 互換）
- `FASTMCP_STATELESS_HTTP=true` — ステートレスモード（リクエスト毎に独立）
- `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=false` — Databricks プロキシ経由のアクセスを許可
