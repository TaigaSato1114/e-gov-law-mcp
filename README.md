# e-Gov法令MCPサーバー

日本政府のe-Gov法令APIに接続する[Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/build-with-claude/mcp)サーバーです。ClaudeなどのLLMから日本の法令文書を簡単に検索・取得できます。

> **初回リリース**: このプロジェクトは初回リリースです。問題が発生した場合は[Issues](https://github.com/ryoooo/e-gov-law-mcp/issues)でお知らせください。

## 機能

- 法令の条文検索（民法192条、憲法第9条など）
- 法令名・種別・キーワードによる検索
- 法令全文の取得（JSON/XML形式）
- 17の主要法令への直接アクセス
- 複雑な条文パターンの対応（325条の3、第9条第2項など）

### 回答内容の特徴

**法律AIエージェントによる詳細分析**
- **条文の正確な全文引用**（一字一句完全表示）
- 立法趣旨と背景の解説
- 要件と法的効果の分析
- 実務上の注意点と関連判例
- 他の条文との関係性

条文を一字一句正確に引用し、その条文を基に詳細な法的分析・解釈を提供します。単なる要約ではなく、正確な条文テキストに基づく専門的な回答です。

## 対応法令

### 六法
- 憲法（昭和二十一年憲法）
- 民法（明治二十九年法律第八十九号）
- 刑法（令和四年法律第六十八号）
- 商法（昭和二十三年法律第二十五号）
- 民事訴訟法（平成八年法律第百九号）
- 刑事訴訟法（昭和二十三年法律第百三十一号）

### その他の重要法令
- 会社法、労働基準法、所得税法、法人税法
- 著作権法、特許法、道路交通法、建築基準法
- 独占禁止法、消費者契約法

## インストール

### 前提条件

[uv](https://docs.astral.sh/uv/)をインストールしてください：

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 方法1: ローカルインストール（推奨）

```bash
# リポジトリをクローン
git clone https://github.com/ryoooo/e-gov-law-mcp.git
cd e-gov-law-mcp

# FastMCP CLIで設定
uvx fastmcp install src/mcp_server.py:mcp -n "e-Gov Law Server"
```

自動的にClaude Desktopの設定が追加されます。

### 方法2: 手動設定

```bash
# リポジトリをクローン
git clone https://github.com/ryoooo/e-gov-law-mcp.git
cd e-gov-law-mcp

# 依存関係をインストール
uv sync
```

その後、Claude Desktopの設定ファイルに手動で追加：

```json
{
  "mcpServers": {
    "e-gov-law": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\path\\to\\e-gov-law-mcp",
        "python",
        "src/mcp_server.py"
      ]
    }
  }
}
```

## Claude Desktop設定

設定ファイルの場所：
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`

### 設定例

```json
{
  "mcpServers": {
    "e-gov-law": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/e-gov-law-mcp",
        "python",
        "src/mcp_server.py"
      ]
    }
  }
}
```

## 利用可能なツール

### find_law_article
条文検索ツール

```python
# 使用例
find_law_article("民法", "192")
find_law_article("会社法", "325条の3")
find_law_article("憲法", "第9条第2項")
```

### search_laws
法令検索ツール

パラメータ：
- `law_title`: 法令名
- `law_type`: 法令種別
- `law_num`: 法令番号
- `limit`: 最大結果数（1-500、デフォルト: 10）

### search_laws_by_keyword
キーワード検索ツール

パラメータ：
- `keyword`: 検索キーワード
- `law_type`: 法令種別フィルタ
- `limit`: 最大結果数（1-20、デフォルト: 5）

### get_law_content
法令全文取得ツール

パラメータ：
- `law_id`: 法令ID
- `law_num`: 法令番号
- `response_format`: "json" または "xml"

## 開発

### 開発環境のセットアップ

```bash
git clone https://github.com/ryoooo/e-gov-law-mcp.git
cd e-gov-law-mcp
uv sync --dev
```

### テスト実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付き
uv run pytest --cov=src
```

### コード品質チェック

```bash
# フォーマット
uv run black src/ tests/

# リント
uv run ruff check src/ tests/

# 型チェック
uv run mypy src/
```

## 使用例

Claude Desktopでの使用：

```
民法192条について教えて
憲法第9条を調べて
会社法325条の3の内容は？
労働基準法で有給休暇について検索して
```

**回答例**（民法192条の場合）：
1. **条文の正確な全文引用**：「第百九十二条　取引行為によって、平穏に、かつ、公然と動産の占有を始めた者は、善意であり、かつ、過失がないときは、即時にその動産について行使する権利を取得する。」
2. 即時取得制度の立法趣旨を解説
3. 「善意」「無過失」「占有」の要件分析
4. 所有権取得の法的効果を説明
5. 実務上の立証責任や関連判例を紹介

プログラムでの使用：

```python
import asyncio
from fastmcp import Client

async def search_example():
    client = Client(["uv", "run", "python", "src/mcp_server.py"])
    
    async with client:
        # 民法192条を検索
        result = await client.call_tool("find_law_article", {
            "law_name": "民法",
            "article_number": "192"
        })
        print(result[0].text)

asyncio.run(search_example())
```

## 設定

環境変数：
- `EGOV_API_URL`: e-Gov APIのベースURL（デフォルト: "https://laws.e-gov.go.jp/api/2"）
- `MCP_SERVER_NAME`: サーバー名

## APIリファレンス

このサーバーは[e-Gov法令API Version 2](https://laws.e-gov.go.jp/api/2/)を使用します。

## ライセンス

MIT License

## 貢献

1. リポジトリをフォーク
2. 機能ブランチを作成
3. 変更を実装
4. テストを追加
5. プルリクエストを作成

## サポート

- [ドキュメント](https://github.com/ryoooo/e-gov-law-mcp#readme)
- [バグレポート](https://github.com/ryoooo/e-gov-law-mcp/issues)
- [ディスカッション](https://github.com/ryoooo/e-gov-law-mcp/discussions)