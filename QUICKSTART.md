# e-Gov Law MCP Server クイックスタートガイド

## 最速セットアップ（15秒で完了）

### uvx一発設定（最も簡単）

Claude Desktopの設定ファイルに以下を追加するだけ：

```json
{
  "mcpServers": {
    "e-gov-law": {
      "command": "uvx",
      "args": ["e-gov-law-mcp"]
    }
  }
}
```

**それだけです！** uvxが自動的にパッケージをダウンロード・実行します。

### FastMCPで自動設定（代替案）

```bash
# Claude Desktopの設定に自動追加
uvx fastmcp install github:ryoooo/e-gov-law-mcp -n "e-Gov Law Server"
```

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