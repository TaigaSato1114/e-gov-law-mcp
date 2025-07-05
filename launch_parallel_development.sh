#!/bin/bash

# 並列開発セッション起動スクリプト
# 開発リーダー用

echo "🚀 並列開発セッションを起動中..."
echo "各worktreeで独立したClaude Codeセッションを開始します"
echo

# 各issueの詳細情報
declare -A ISSUES=(
    ["issue-6-fix"]="Issue #6: 法令取得失敗の修正 - 特定受託事業者に係る取引の適正化等に関する法律"
    ["issue-1-terminology"]="Issue #1: 法律用語の正確性改善 - 構成要件→要件等の修正"
    ["issue-4-prompts"]="Issue #4: プロンプトとコードの分離 - プロンプトの外部化"
    ["issue-3-config"]="Issue #3: 法令マッピング設定の外部化 - BASIC_LAWSの設定ファイル化"
    ["issue-5-performance"]="Issue #5: APIリクエスト最適化 - キャッシュとパフォーマンス改善"
    ["issue-2-external"]="Issue #2: 外部情報源活用の検討 - 外部情報源の活用検討"
)

# 優先度順序
declare -a PRIORITY_ORDER=(
    "issue-6-fix"
    "issue-1-terminology"
    "issue-4-prompts"
    "issue-3-config"
    "issue-5-performance"
    "issue-2-external"
)

echo "📋 開発計画:"
echo "============"
for issue in "${PRIORITY_ORDER[@]}"; do
    echo "🔹 $issue: ${ISSUES[$issue]}"
done
echo

# 手動起動用のコマンドを生成
echo "🔧 手動起動用コマンド:"
echo "====================="
echo "以下のコマンドを6つの異なるターミナルで実行してください:"
echo

counter=1
for issue in "${PRIORITY_ORDER[@]}"; do
    echo "# ターミナル$counter: $issue"
    echo "cd /home/ryoki/dev/worktrees/$issue"
    echo "claude --dangerously-skip-permissions"
    echo
    ((counter++))
done

echo "🎯 各Claude Codeセッションでの作業指示:"
echo "========================================"

# Issue #6の指示
echo "【Issue #6 - 法令取得失敗修正】"
echo "1. 現在のBASIC_LAWSマッピングを確認"
echo "2. e-Gov APIで「特定受託事業者に係る取引の適正化等に関する法律」を検索"
echo "3. 正しい法律番号を特定してマッピングを修正"
echo "4. テストケースを追加"
echo "5. 修正をコミット"
echo

# Issue #1の指示
echo "【Issue #1 - 法律用語修正】"
echo "1. src/mcp_server.pyのlegal_analysis_instructionを確認"
echo "2. '構成要件'→'要件'への修正"
echo "3. 法的効果の説明を強化"
echo "4. 専門用語の一貫性を確保"
echo "5. 修正をコミット"
echo

# Issue #4の指示
echo "【Issue #4 - プロンプト分離】"
echo "1. prompts/ディレクトリを作成"
echo "2. legal_analysis.mdファイルを作成"
echo "3. PromptLoaderクラスを実装"
echo "4. 既存のハードコーディングされたプロンプトを移行"
echo "5. 後方互換性を確保"
echo "6. 修正をコミット"
echo

# Issue #3の指示
echo "【Issue #3 - 設定外部化】"
echo "1. config/laws.yamlファイルを作成"
echo "2. ConfigLoaderクラスを実装"
echo "3. BASIC_LAWSとLAW_ALIASESをYAMLに移行"
echo "4. 環境変数による設定パス指定をサポート"
echo "5. 後方互換性を確保"
echo "6. 修正をコミット"
echo

# Issue #5の指示
echo "【Issue #5 - パフォーマンス最適化】"
echo "1. LRUキャッシュクラスを実装"
echo "2. 法律データのインメモリキャッシュ"
echo "3. バッチリクエスト機能の検討"
echo "4. プリフェッチ機能の実装"
echo "5. メモリ使用量の監視"
echo "6. 修正をコミット"
echo

# Issue #2の指示
echo "【Issue #2 - 外部情報源統合】"
echo "1. 政府機関ホワイトリスト（go.jp, courts.go.jp）の作成"
echo "2. 外部情報源のプラグインシステム設計"
echo "3. オプトイン方式の実装"
echo "4. 最高裁判例データベースとの連携検討"
echo "5. 設定可能な外部参照機能の実装"
echo "6. 修正をコミット"
echo

echo "🎉 全ての並列開発セッションを起動して、効率的な開発を開始してください！"