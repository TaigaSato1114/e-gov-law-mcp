# e-Gov Law MCP Server クイックスタートガイド

## 最速セットアップ（15秒で完了）

### FastMCP設定（最も簡単）

```bash
# 1. リポジトリをクローン
git clone https://github.com/ryoooo/e-gov-law-mcp.git
cd e-gov-law-mcp

# 2. FastMCP CLIで設定
uvx fastmcp install src/mcp_server.py:mcp -n "e-Gov Law Server"
```

**それだけです！** 自動的にClaude Desktopの設定が追加されます。

## 使い方

Claude Desktopを再起動後、以下のように質問してください：

```
民法192条を教えて
憲法9条について説明して
会社法325条の3を調べて
労働基準法の有給休暇について検索して
```

## トラブルシューティング

### uvxがインストールされていない場合

```bash
# uvをインストール（uvxも含まれます）
curl -LsSf https://astral.sh/uv/install.sh | sh

# または
pip install uv
```

### Windows環境の場合

PowerShellで実行：
```powershell
# uvのインストール
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# e-Gov Lawサーバーの設定
uvx fastmcp install github:ryoooo/e-gov-law-mcp -n "e-Gov Law Server"
```

### 詳細な設定方法

より詳しい設定方法は[README.md](README.md)を参照してください。