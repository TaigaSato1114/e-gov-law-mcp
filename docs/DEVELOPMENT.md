# 開発ガイド（Databricks Genie Code向け）

このドキュメントは、Databricksワークスペースと本GitHubリポジトリが連携済み（Git folder / Repos連携済み）であることを前提に、Databricks Genie Code（AIコーディングエージェント）へ本プロジェクトの改修・デプロイを指示するための資料です。

## 前提条件

- Databricksワークスペースの Git folder（Repos）機能で本リポジトリが同期済みであること
- 対象ブランチで作業し、変更は最終的に GitHub 側へ push（またはPR作成）すること
- 本サーバーは Databricks Apps 上で **streamable-http transport** のMCPサーバーとして稼働する（Claude Desktop向けの `stdio` transportも後方互換として残っている）

## プロジェクト構造

```
e-gov-law-mcp/
├── src/
│   └── mcp_server.py      # メインのMCPサーバー実装
├── examples/              # 使用例（一次資料として保持。stdio接続の例のため参考程度に）
├── tests/                 # テストファイル
├── docs/                  # ドキュメント
│   ├── USAGE.md
│   ├── DEVELOPMENT.md     # このファイル
│   └── rules/COMMIT_RULE.md
├── .plan/                 # 設計・対処方法などの作業記録
├── app.yaml               # Databricks Apps 起動コマンド定義
├── requirements.txt       # Databricks Apps ビルド時依存（uvのみ）
├── pyproject.toml         # プロジェクト設定・依存関係・entry point
├── uv.lock
└── README.md
```

## Genie Codeへの指示の出し方（推奨フロー）

1. **変更内容を明確に指示する**: 「〜ツールを追加して」「〜のバグを修正して」など、対象ファイル（主に`src/mcp_server.py`）を明示する
2. **コミット規約に従わせる**: [docs/rules/COMMIT_RULE.md](rules/COMMIT_RULE.md) の `<type>(<scope>): <description>` 形式を守らせる
3. **ローカル検証をさせてから終える**: 下記「開発ワークフロー」のフォーマット・リント・テストを実行させ、失敗があれば修正させる
4. **Databricks Apps環境での起動確認をさせる**（コード変更が起動ロジックやtransportに関わる場合）: 下記「Databricks Appsへのデプロイ」節の手順で `streamable-http` 起動を確認させる

## 開発環境のセットアップ

### 前提条件

- Python 3.12（`.python-version` で固定。詳細は後述のトラブルシューティング参照）
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー

### セットアップ手順

```bash
# 開発依存関係を含む全ての依存関係をインストール
uv sync --dev

# pre-commitフックをインストール（推奨）
uv run pre-commit install
```

## 開発ワークフロー

### 1. コード作成

```bash
# コードフォーマットを実行
uv run black src/ tests/ examples/

# リント検査を実行
uv run ruff check src/ tests/ examples/

# 型チェックを実行
uv run mypy src/
```

### 2. テスト実行

```bash
# 全テストを実行
uv run pytest

# カバレッジレポート付きで実行
uv run pytest --cov=src --cov-report=html

# 特定のテストファイルのみ実行
uv run pytest tests/test_mcp_server.py -v
```

### 3. ローカルでのMCPサーバー起動確認

```bash
# stdio transport（Claude Desktop互換の確認用）
uv run e-gov-law-mcp

# streamable-http transport（Databricks Apps相当の確認用）
DATABRICKS_APP_PORT=8000 uv run e-gov-law-mcp --transport streamable-http
# → http://0.0.0.0:8000/mcp で応答することを確認
```

## 新機能の追加

### 1. 新しいツールの追加

```python
@mcp.tool
async def new_tool(param1: str, param2: int = 10) -> str:
    """
    新しいツールの説明

    Args:
        param1: パラメータ1の説明
        param2: パラメータ2の説明（デフォルト: 10）

    Returns:
        結果の説明
    """
    if not param1:
        raise ToolError("param1 is required")

    async with await get_http_client() as client:
        response = await client.get("/new-endpoint", params={"param1": param1})
        response.raise_for_status()
        return response.text
```

### 2. 新しいリソースの追加

```python
@mcp.resource("schema://new_resource")
def get_new_resource() -> dict:
    """新しいリソースの説明"""
    return {
        "data": "リソースデータ",
        "metadata": {"version": "1.0", "description": "説明"}
    }
```

### 3. テストの追加

```python
class TestNewFeature:
    @pytest.mark.asyncio
    async def test_new_tool_success(self):
        """新しいツールの成功ケースをテスト"""
        pass

    @pytest.mark.asyncio
    async def test_new_tool_validation(self):
        """新しいツールの入力検証をテスト"""
        pass
```

## Databricks Appsへのデプロイ

コード変更をGitHub側にpushした後、Databricksワークスペース側で以下を実行してApp本体をデプロイする。

```bash
# 1. OAuth認証（初回のみ）
databricks auth login --host https://<your-workspace-hostname>

# 2. コードをワークスペースへ同期
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks sync . "/Workspace/Users/$DATABRICKS_USERNAME/mcp-e-gov-law"

# 3. Databricks Appとしてデプロイ
databricks apps deploy mcp-e-gov-law \
  --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/mcp-e-gov-law"
```

デプロイ完了後、`https://<app-url>/mcp` がMCPエンドポイントとして公開される。Playground・サービングエンドポイントからの利用登録手順は [USAGE.md](USAGE.md) を参照。

## Databricks Appsデプロイ時のトラブルシューティング

デプロイが失敗する、またはAppsが起動直後にクラッシュする場合は、まず Apps UI の **Logs タブ（ソースフィルタ: APP）** でスタックトレースを確認する。

| ログ内のキーワード | 意味 | 対処 |
|---|---|---|
| `ImportError` / `ModuleNotFoundError` | パッケージ間のバージョン不整合 | `uv.lock` を再生成（`uv lock --python 3.12`） |
| `maturin failed` / `cargo` / `pyo3` | 使用中のPythonバージョン用ホイールが存在しない | `.python-version` の値、および `pyproject.toml` の `requires-python` を確認 |
| `TypeError: cannot specify both default and default_factory` | pydanticのバージョン非互換 | pydanticのバージョン制約を調整 |
| `502 Bad Gateway` / `App Not Available` | アプリプロセスが起動していない | 上記いずれかの起動エラーが原因。Logsタブで APP ログを確認 |

### 根本原因の実例（2026-07-06発生）

`uv` が `pyproject.toml` の `requires-python = ">=3.12"` を解釈し、コンテナ内で **Python 3.14 をダウンロードして使用**したことが原因で、`pydantic-core` のビルド済みホイールが存在せず起動に失敗した。

```
Python reports SOABI: cpython-314-x86_64-linux-gnu
error: the configured Python interpreter version (3.14) is newer than
PyO3's maximum supported version (3.13)
```

**解決策**: リポジトリルートに `.python-version`（内容: `3.12`）を配置し、`uv` が使用するPythonバージョンを固定。`uv.lock` も `uv lock --python 3.12` で再生成した。

### 予防策（Genie Codeが変更を加える際に守るべき事項）

1. **`.python-version` を常にリポジトリに含める**（削除・変更しない）
   - `uv` の最新Python自動ダウンロードを防止し、Databricks Appsコンテナがサポートする Python 3.12 に固定する
2. **依存関係を変更した場合は `uv lock --python 3.12` でロックファイルを再生成する**
3. **ワークスペースの同期対象に `.venv` を含めない**
   - `uv sync` はシンボリックリンクを含む `.venv` を生成し、Databricks Apps はシンボリックリンクをエクスポートできず `type=symlink` エラーになる
   - ロックファイル生成のみが必要な場合は `uv sync` ではなく `uv lock` を使う
4. **`fastmcp` のバージョン制約に注意**: `fastmcp>=2.8.1,<3.0.0`（3.x系は `typing_extensions.Sentinel` 問題があるため固定）
5. **診断を依頼する際は以下の情報を提供する**
   - Apps UIのAPPログのスタックトレース全文
   - `app.yaml` の内容
   - `pyproject.toml` の `dependencies` / `requires-python`
   - `.python-version` の内容
   - `uv.lock` の主要パッケージバージョン（`grep -E '^(name|version)' uv.lock | grep -B1 'pydantic\|fastmcp\|mcp'`）

### 現在の正常動作構成（参考）

| ファイル | 内容 |
|---|---|
| `.python-version` | `3.12` |
| `pyproject.toml` | `requires-python = ">=3.12"`, `fastmcp>=2.8.1,<3.0.0` |
| `app.yaml` | `sh -c` 経由でFastMCP用環境変数を設定 + `uv run e-gov-law-mcp --transport streamable-http` |
| `uv.lock` | `fastmcp==2.14.7`, `pydantic==2.13.4`, `pydantic-core==2.46.4` |

`app.yaml` の環境変数の意味:
- `FASTMCP_JSON_RESPONSE=true` — SSEではなくJSONレスポンスを返す（Playground互換）
- `FASTMCP_STATELESS_HTTP=true` — ステートレスモード（リクエスト毎に独立）
- `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=false` — Databricksプロキシ経由のアクセスを許可

## コーディング規約

- **言語**: 日本語のコメントとドキュメント
- **フォーマット**: Black、Ruffを使用
- **型ヒント**: 必須
- **テスト**: 新機能には必ずテストを追加
- **コミットメッセージ**: [docs/rules/COMMIT_RULE.md](rules/COMMIT_RULE.md) を参照

## トラブルシューティング（開発一般）

1. **依存関係の競合**
   ```bash
   uv sync --reinstall
   ```

2. **テストの失敗**
   ```bash
   uv run pytest -v --tb=short
   ```

3. **型エラー**
   ```bash
   uv run mypy src/ --show-error-codes
   ```
