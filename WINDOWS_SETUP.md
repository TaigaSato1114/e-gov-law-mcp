# Windows環境でのセットアップ手順

このガイドでは、Windows環境でe-Gov法令MCPサーバーv2をClaude Desktopで使用するための詳細なセットアップ手順を説明します。

## 前提条件

### 1. uvの安装

Windows環境でuvを安装します：

```powershell
# PowerShellで実行
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

または

```cmd
# コマンドプロンプトで実行
pip install uv
```

### 2. Gitのクローン

プロジェクトをクローンします：

```cmd
git clone https://github.com/ryoooo/e-gov-law-mcp.git
cd e-gov-law-mcp
```

## セットアップ

### 1. 依存関係のインストール

```cmd
# 依存関係をインストール
uv sync
```

### 2. 動作確認

```cmd
# サーバーの動作確認
uv run python src/mcp_server.py --help

# テストの実行
uv run pytest tests/ -v
```

## Claude Desktop設定

### 1. 設定ファイルの場所

Claude Desktopの設定ファイルは以下の場所にあります：

```
%APPDATA%\\Claude\\claude_desktop_config.json
```

実際のパス例：
```
C:\\Users\\[ユーザー名]\\AppData\\Roaming\\Claude\\claude_desktop_config.json
```

### 2. 設定ファイルの編集

#### ネイティブWindows環境の場合

設定ファイルに以下を追加します：

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
      ],
      "env": {
        "EGOV_API_URL": "https://laws.e-gov.go.jp/api/2"
      }
    }
  }
}
```

**重要:** `C:\\path\\to\\e-gov-law-mcp` を実際のプロジェクトパスに変更してください。

#### WSL（Windows Subsystem for Linux）環境の場合

WSLでプロジェクトを実行する場合は以下の設定を使用します：

```json
{
  "mcpServers": {
    "e-gov-law": {
      "command": "wsl",
      "args": [
        "-e",
        "bash",
        "-l",
        "-c",
        "cd /home/username/dev/e-gov-law-mcp-github && uv run python src/mcp_server.py"
      ],
      "env": {
        "EGOV_API_URL": "https://laws.e-gov.go.jp/api/2"
      }
    }
  }
}
```

**重要:** 
- `/home/username/dev/e-gov-law-mcp-github` をWSL内の実際のプロジェクトパスに変更してください
- GitHubからクローンした場合、フォルダ名は通常 `e-gov-law-mcp-github` になります

### 3. パスの確認方法

#### ネイティブWindowsの場合：

```cmd
cd e-gov-law-mcp-github
echo %CD%
```

出力例：
```
C:\Users\YourName\Documents\e-gov-law-mcp
```

#### WSLの場合：

```bash
cd e-gov-law-mcp
pwd
```

出力例：
```
/home/ryoki/dev/e-gov-law-mcp-github
```

この場合、設定ファイルには以下のように記入します：

```json
{
  "mcpServers": {
    "e-gov-law": {
      "command": "wsl",
      "args": [
        "-e",
        "bash",
        "-l",
        "-c",
        "cd /home/ryoki/dev/e-gov-law-mcp-github && uv run python src/mcp_server.py"
      ],
      "env": {
        "EGOV_API_URL": "https://laws.e-gov.go.jp/api/2"
      }
    }
  }
}
```

## FastMCP CLI使用（推奨・最も簡単）

FastMCPはプロジェクトの依存関係に含まれているため、`uv run`を使用して直接実行できます：

### 自動インストール（1コマンドで完了）

プロジェクトディレクトリで実行：

```cmd
uv run fastmcp install src/mcp_server.py:mcp -n "e-Gov Law Server"
```

これにより：
- ✅ Claude Desktop設定が自動的に更新される
- ✅ 正しいパスが自動的に設定される
- ✅ 必要な依存関係が自動的に含まれる
- ✅ Windows環境に最適化された設定が適用される

### インストール確認

インストール後、Claude Desktopを再起動して、以下のコマンドで確認：

```
e-Gov法令で民法192条を調べて
```

## トラブルシューティング

### 1. uvが見つからない場合

```cmd
# PATH環境変数を確認
echo %PATH%

# uvのパスを確認
where uv
```

uvが見つからない場合は、PowerShellを再起動するか、手動でPATHに追加してください。

### 2. 権限エラー

Windows Defenderやウイルス対策ソフトがuvの実行を阻害する場合があります。その場合は、例外設定を追加してください。

### 3. Claude Desktopでサーバーが認識されない場合

1. Claude Desktopを完全に終了
2. 設定ファイルの構文を確認（JSONが正しいか）
3. パスにスペースが含まれている場合は、適切にエスケープされているか確認
4. Claude Desktopを再起動

### 4. ログの確認

Claude Desktopのログは以下で確認できます：

```
%APPDATA%\\Claude\\logs\\
```

## 動作確認

Claude Desktopで以下のように問い合わせて動作を確認してください：

```
民法192条について教えてください
```

正常に動作している場合、即時取得に関する条文が表示されます。

## 最新情報

このプロジェクトの最新情報については、GitHubリポジトリを確認してください：
https://github.com/ryoooo/e-gov-law-mcp