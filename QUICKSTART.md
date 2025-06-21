# 🚀 e-Gov法令MCP v2 クイックスタートガイド

## 最速セットアップ（3ステップ・5分で完了）

### ステップ 1: uvのインストール（30秒）

#### Windows
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### ステップ 2: プロジェクトのセットアップ（2分）

```bash
# プロジェクトをクローン
git clone https://github.com/ryoooo/e-gov-law-mcp.git
cd e-gov-law-mcp

# 依存関係をインストール
uv sync
```

### ステップ 3: Claude Desktopへの自動インストール（30秒）

```bash
# 1コマンドで完了！
uv run fastmcp install src/mcp_server.py:mcp -n "e-Gov Law Server"
```

**完了！** Claude Desktopを再起動すれば使えます。

## 動作確認

Claude Desktopで以下のように質問してみてください：

```
民法192条について教えて
```

または

```
会社法325条の3の内容を調べて
```

## 詳細設定

より詳しい設定については：
- [Windows環境の詳細設定](WINDOWS_SETUP.md)
- [完全なREADME](README.md)

## トラブルシューティング

### Q: uvコマンドが見つからない
A: ターミナル/PowerShellを再起動してください

### Q: Claude Desktopでサーバーが認識されない
A: Claude Desktopを完全に終了して再起動してください

### Q: エラーが出る
A: `uv run pytest tests/` でテストを実行して問題を確認してください