# [詳細設計] Databricks Playground / Serving Endpoint向けカスタムMCP対応

## 概要（Summary）

現状の e-Gov Law MCP Server は Claude Desktop などの `stdio` transport を前提とした MCP クライアントからのみ利用可能。
本対応では、Databricks 上でホストされる全サービングエンドポイント・Databricks Playground から利用できるよう、本サーバーを **Databricks Apps 上でカスタムMCPサーバーとして稼働させる** ための最小限の変更を行う。

- サーバー本体のツール・ロジックには変更を加えない（8ツール・2リソースはそのまま）
- 既存の Claude Desktop 向け `stdio` 起動経路は維持し、後方互換を保つ
- 新たに Databricks Apps が要求する起動条件（`0.0.0.0` バインド、`DATABRICKS_APP_PORT` によるポート指定、HTTPトランスポート）に対応する

## 背景・課題（Why）

- e-Gov Law MCP は現在 Claude Desktop 専用の `stdio` 起動のみが実運用されている
- Databricks Playground / Mosaic AI Agent Framework 経由でツールを使うには、MCPサーバーが **streamable HTTP transport** で稼働し、Unity AI Gateway に「カスタムMCPサーバー」として登録できる形（= Databricks Apps としてデプロイ可能な形）である必要がある
- Databricks Apps はコンテナ内プロセスに対して `DATABRICKS_APP_PORT` 環境変数でリスンポートを指定し、`0.0.0.0` でのバインドを要求する。現状のデフォルト実装（`--host 127.0.0.1`）はこの要件を満たさない

## 対応方針（Approach）

1. サーバー起動部分（`src/mcp_server.py: main()`）に Databricks Apps 環境検知ロジックを追加し、`DATABRICKS_APP_PORT` が設定されている場合は自動的に `0.0.0.0` ＋ 該当ポートで起動するようデフォルト値を調整する
2. Databricks Apps のデプロイに必要な `app.yaml` / `requirements.txt` を追加する（既存の `pyproject.toml` の entry point `e-gov-law-mcp` をそのまま起動コマンドとして利用）
3. コード変更は最小限に留め、既存の `--transport stdio`（Claude Desktop向け）動作に影響を与えない
4. Databricks側の設定作業（Apps デプロイ・Unity Catalog 権限付与・Playground/Serving Endpoint からの接続）は別途運用手順として記載し、リポジトリ外の作業として明示する

## 変更ファイル一覧（Files Changed）

| ファイル | 種別 | 概要 |
|---|---|---|
| `src/mcp_server.py` | 変更 | `main()` の `--host` / `--port` デフォルト値を Databricks Apps 環境向けに自動切り替え |
| `app.yaml` | 新規 | Databricks Apps の起動コマンド定義 |
| `requirements.txt` | 新規 | Databricks Apps のビルド時依存（`uv` のみ） |

---

## 詳細変更内容（Diff Detail）

### 1. `src/mcp_server.py`

**変更箇所**: `main()` 関数（ファイル末尾、旧 1428〜1446行目付近）

**変更前**:
```python
def main():
    """Entry point for direct uvx installation"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="e-Gov Law MCP Server v2")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "stdio":
        # Use FastMCP's built-in stdio support
        mcp.run()
    else:
        # Use FastMCP's built-in streamable-http transport
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port
        )
```

**変更後**:
```python
def main():
    """Entry point for direct uvx installation"""
    # Parse command line arguments
    # Databricks Apps injects DATABRICKS_APP_PORT and expects the process to
    # bind 0.0.0.0, so those env vars become the defaults when present.
    running_as_databricks_app = "DATABRICKS_APP_PORT" in os.environ
    default_host = "0.0.0.0" if running_as_databricks_app else "127.0.0.1"

    parser = argparse.ArgumentParser(description="e-Gov Law MCP Server v2")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default=os.environ.get("MCP_HOST", default_host))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("DATABRICKS_APP_PORT", os.environ.get("MCP_PORT", 8000)))
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        # Use FastMCP's built-in stdio support
        mcp.run()
    else:
        # Use FastMCP's built-in streamable-http transport
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port
        )
```

**変更理由**:
- Databricks Apps はコンテナ起動時に `DATABRICKS_APP_PORT` 環境変数でリスンポートを渡し、プロセスは `0.0.0.0` でバインドする必要がある（`127.0.0.1` 固定のままだとApps基盤からのリクエストがコンテナに到達しない）
- `DATABRICKS_APP_PORT` の有無で自動判定することで、Databricks Apps用の起動コマンドに特別な `--host`/`--port` 引数を明示しなくても正しく動作する
- `MCP_HOST` / `MCP_PORT` という汎用環境変数も合わせて用意し、Databricks Apps以外の環境（Docker等）でも環境変数経由で上書きできるようにした
- `--transport stdio`（Claude Desktop向けデフォルト経路）は今回のロジックに一切触れないため、既存動作への影響はない

**影響範囲**:
- `--transport streamable-http` を明示的に指定した場合のみ関係するロジック。既存の `stdio` 利用者（Claude Desktop）には影響なし
- `--host` / `--port` を明示的にCLI引数で渡していた既存の運用（もしあれば）は、引数指定が優先されるため互換性は保たれる

---

### 2. `app.yaml`（新規）

```yaml
# Databricks Apps launch configuration.
# Runs the existing FastMCP entry point over streamable-http so the server
# can be reached at https://<app-url>/mcp from Playground / serving endpoints.
command: ['uv', 'run', 'e-gov-law-mcp', '--transport', 'streamable-http']
```

**追加理由**:
- Databricks Apps はワークスペースにデプロイされたソースコードのルートにある `app.yaml` の `command` を起動コマンドとして実行する
- `pyproject.toml` に既存定義済みの `[project.scripts] e-gov-law-mcp = "src.mcp_server:main"` エントリポイントをそのまま `uv run` 経由で呼び出す構成とし、Databricks Apps専用の起動スクリプトを別途作成する必要をなくした
- `--host` / `--port` は明示せず、`main()` 側の環境変数自動判定に委ねる

---

### 3. `requirements.txt`（新規）

```text
# Databricks Apps only needs `uv` itself; `uv run` resolves the rest of the
# dependency graph from pyproject.toml / uv.lock at container start.
uv
```

**追加理由**:
- Databricks Apps はデプロイ時に `requirements.txt` があれば `pip install -r requirements.txt` を実行してからアプリを起動する。本リポジトリは `uv` + `pyproject.toml` / `uv.lock` で依存関係を管理しているため、Apps側のPython環境には `uv` コマンドのみをインストールし、実際の依存解決（`fastmcp`, `httpx`, `PyYAML` 等）は起動時に `uv run` が `uv.lock` を用いて行う

---

## 動作確認（Verification）

ローカル環境で Databricks Apps 相当の条件（`DATABRICKS_APP_PORT` 環境変数のみ設定、`--host`/`--port` は指定しない）で起動確認済み。

```bash
DATABRICKS_APP_PORT=8123 uv run e-gov-law-mcp --transport streamable-http
```

**ログ出力**（該当部分）:
```
INFO  Starting MCP server 'e-Gov Law API Server v2' with transport 'streamable-http' on http://0.0.0.0:8123/mcp
INFO:     Uvicorn running on http://0.0.0.0:8123 (Press CTRL+C to quit)
```

- `0.0.0.0:8123` に正しくバインドされることを確認（`DATABRICKS_APP_PORT` から自動でホスト/ポートが解決されている）
- `curl http://127.0.0.1:8123/mcp` → `HTTP 307`（streamable-httpのセッション確立要求によるリダイレクトで、MCPエンドポイントとして正常応答）
- 既存の `stdio` 起動（`uv run e-gov-law-mcp`、引数なし）は変更ロジックの分岐に入らないため、リグレッションなし

未実施・別途要確認の項目（リポジトリ外の作業）:
- 実際の Databricks ワークスペースへの `databricks apps deploy` 実施と、Apps基盤からのヘルスチェック通過確認
- e-Gov法令APIへのアウトバウンド通信が Databricks Apps のネットワーク環境から到達可能かの確認
- 複数レプリカ稼働時、プロセスローカルなLRUキャッシュ・`psutil`メモリ監視がレプリカ単位で独立して動作する点の運用上の許容確認

---

## デプロイ・運用手順（Databricksワークスペース側、リポジトリ外作業）

コード変更のマージ後、以下をワークスペース側で実施する。

### Phase A: Databricks Appsとしてデプロイ

```bash
# 1. OAuth認証
databricks auth login --host https://<your-workspace-hostname>

# 2. コードをワークスペースへ同期
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks sync . "/Workspace/Users/$DATABRICKS_USERNAME/mcp-e-gov-law"

# 3. Databricks Appとしてデプロイ（アプリ名は mcp- prefix推奨）
databricks apps deploy mcp-e-gov-law \
  --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/mcp-e-gov-law"
```

デプロイ完了後、`https://<app-url>/mcp` がMCPエンドポイントとして公開される。

### Phase B: Unity AI Gateway / Unity Catalog への登録

1. Unity AI Gatewayの「MCPサーバー管理」画面で、上記App URLをカスタムMCPサーバーとして登録
2. Unity Catalogの権限管理で、本MCPサーバーへの `USE` 権限を対象範囲に付与
   - 「すべてのサービングエンドポイントで利用可能」にする場合、各サービングエンドポイントが用いるサービスプリンシパル、またはワークスペース全体を対象とするグループに対して権限を付与する

### Phase C: 利用側の設定・動作確認

1. Databricks Playgroundのツール一覧から本MCPサーバーを追加し、法令検索系ツール（`find_law_article` 等）を実行して応答を確認
2. Mosaic AI Agent Framework等でサービングエンドポイント経由で利用する場合、`databricks-mcp` ライブラリ等でこのMCPサーバーURLに接続するコードをエージェント定義側に追加
3. Unity AI Gatewayのログでアクセス状況・エラーの有無をモニタリング

### 運用上の留意点

- Databricks Apps は常時起動コンテナとして課金対象になるため、事前にコストを確認すること
- 既存の Claude Desktop 向け `stdio` 起動と、Databricks Apps 向け `streamable-http` 起動は同一コードベースから引数のみで切り替わるため、両方の利用形態を今後も共存させることが可能

---

## ロールバック方針（Rollback）

- `src/mcp_server.py` の変更は `main()` 内のデフォルト値決定ロジックのみであり、CLI引数で明示的に `--host` / `--port` を指定すれば従来動作に戻せる
- 問題が生じた場合は本コミットを `git revert` するか、Databricks Apps自体を削除すれば Claude Desktop向けの既存運用への影響はない
