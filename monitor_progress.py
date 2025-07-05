#!/usr/bin/env python3
"""
並列開発プロジェクトの進捗監視スクリプト
開発リーダー用の監視ツール
"""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

WORKTREE_BASE = "/home/ryoki/dev/worktrees"
WORKTREES = [
    "issue-6-fix",
    "issue-1-terminology", 
    "issue-4-prompts",
    "issue-3-config",
    "issue-5-performance",
    "issue-2-external"
]

ISSUE_DESCRIPTIONS = {
    "issue-6-fix": "法令取得失敗修正",
    "issue-1-terminology": "法律用語修正",
    "issue-4-prompts": "プロンプト分離",
    "issue-3-config": "設定外部化",
    "issue-5-performance": "パフォーマンス最適化",
    "issue-2-external": "外部情報源統合"
}

def get_git_status(worktree_path):
    """指定されたworktreeのgit statusを取得"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_latest_commit(worktree_path):
    """最新のコミット情報を取得"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def monitor_progress():
    """全worktreeの進捗を監視"""
    print("=" * 80)
    print(f"🚀 並列開発進捗監視 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    for worktree in WORKTREES:
        worktree_path = Path(WORKTREE_BASE) / worktree
        
        print(f"\n📁 {worktree} - {ISSUE_DESCRIPTIONS.get(worktree, 'Unknown')}")
        print("-" * 60)
        
        if not worktree_path.exists():
            print("❌ Worktree not found")
            continue
            
        # Git status
        status = get_git_status(worktree_path)
        if status:
            print(f"📝 変更あり: {len(status.splitlines())} files")
        else:
            print("✅ 変更なし")
            
        # Latest commit
        commit = get_latest_commit(worktree_path)
        print(f"📊 最新コミット: {commit}")
        
        # Check for specific files
        key_files = {
            "issue-6-fix": ["src/mcp_server.py"],
            "issue-1-terminology": ["src/mcp_server.py"],
            "issue-4-prompts": ["prompts/", "src/mcp_server.py"],
            "issue-3-config": ["config/", "src/mcp_server.py"],
            "issue-5-performance": ["src/mcp_server.py"],
            "issue-2-external": ["src/mcp_server.py"]
        }
        
        if worktree in key_files:
            for file_path in key_files[worktree]:
                full_path = worktree_path / file_path
                if full_path.exists():
                    print(f"✅ {file_path} 存在")
                else:
                    print(f"❌ {file_path} 未作成")

def main():
    """メイン関数"""
    try:
        while True:
            monitor_progress()
            print("\n" + "=" * 80)
            print("🔄 30秒後に再チェック... (Ctrl+C で終了)")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n\n🛑 監視を終了します。")

if __name__ == "__main__":
    main()