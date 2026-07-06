# 使用方法ガイド（Databricks Apps / カスタムMCP）

## 基本的な使用方法

### 1. サーバーの起動（Databricks Apps）

本サーバーは Databricks Apps 上に streamable-http transport でデプロイされ、`https://<app-url>/mcp` で公開される。起動コマンドは `app.yaml` に定義済みで、Apps基盤がコンテナ起動時に自動実行する。手動での起動操作は不要。

ローカルで動作確認したい場合:

```bash
DATABRICKS_APP_PORT=8000 uv run e-gov-law-mcp --transport streamable-http
# → http://0.0.0.0:8000/mcp で応答
```

### 2. Databricks Appsへのデプロイ

```bash
databricks auth login --host https://<your-workspace-hostname>

DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks sync . "/Workspace/Users/$DATABRICKS_USERNAME/mcp-e-gov-law"

databricks apps deploy mcp-e-gov-law \
  --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/mcp-e-gov-law"
```

デプロイ時のトラブルシューティングは [DEVELOPMENT.md](DEVELOPMENT.md) を参照。

### 3. Unity AI Gatewayへの登録

1. Unity AI Gatewayの「MCPサーバー管理」画面で、デプロイ済みのApp URL（`https://<app-url>/mcp`）をカスタムMCPサーバーとして登録する
2. Unity Catalogの権限管理で、本MCPサーバーへの `USE` 権限を対象範囲（利用させたいサービングエンドポイントのサービスプリンシパル、または対象ユーザー/グループ）に付与する

### 4. Databricks Playgroundでの利用

1. Databricks Playgroundを開き、ツール一覧から本MCPサーバーを追加する
2. チャット上で法令に関する質問を送ると、登録済みツールが自動的に呼び出される

```
民法192条について詳しく教えて
憲法第9条第2項の条文と解釈を知りたい
会社法325条の3の株主総会決議について
労働基準法の有給休暇の規定を調べて
道路交通法の飲酒運転の罰則は？
```

### 5. サービングエンドポイント（Agent Framework等）からの利用

Mosaic AI Agent Framework等でエージェントを構築する場合、MCPクライアント経由で本サーバーのURL（`https://<app-url>/mcp`）に接続するツール定義をエージェント側に追加する。Unity Catalogで対象サービングエンドポイントのサービスプリンシパルに `USE` 権限が付与されていることが前提。

## ツールの詳細

### search_laws - 法令検索

日本の法令・規則を検索します。

**パラメータ:**
- `law_title` (オプション): 法令名での部分一致検索
- `law_type` (オプション): 法令種別での絞り込み
- `limit` (オプション): 取得件数の上限（1-100、デフォルト: 10）
- `offset` (オプション): 開始位置（デフォルト: 0）

**使用例:**
```json
{
  "law_title": "民法",
  "law_type": "Act",
  "limit": 5
}
```

**法令種別の値:**
- `Constitution`: 憲法
- `Act`: 法律
- `CabinetOrder`: 政令
- `ImperialOrder`: 勅令
- `MinisterialOrdinance`: 府省令
- `Rule`: 規則
- `Misc`: その他

### search_laws_by_keyword - キーワード検索

法令本文内でのキーワード全文検索を実行します。

**パラメータ:**
- `keyword` (必須): 検索キーワード
- `law_type` (オプション): 法令種別での絞り込み
- `limit` (オプション): 取得件数の上限（1-20、デフォルト: 5）

**使用例:**
```json
{
  "keyword": "契約",
  "law_type": "Act",
  "limit": 10
}
```

### get_law_content - 法令本文取得

指定した法令の全文内容を取得します。

**パラメータ:**
- `law_id` または `law_num` (どちらか必須): 法令の識別子
- `response_format` (オプション): "json" または "xml"（デフォルト: "json"）

**使用例:**
```json
{
  "law_num": "明治二十九年法律第八十九号",
  "response_format": "json"
}
```

### find_law_article - 条文検索

法令名と条数から該当条文を検索します。

### batch_find_articles - バッチ検索

複数の条文検索を一括実行します（最大200件）。

### prefetch_common_laws / get_cache_stats / clear_cache

キャッシュの事前読み込み・統計取得・クリアを行うメンテナンス用ツールです。

## リソース

### api://info

e-Gov法令APIの基本情報と機能一覧を取得できます。

### schema://law_types

利用可能な法令種別とその説明を取得できます。

## エラーハンドリング

### 一般的なエラー

- **入力検証エラー**: パラメータが無効な場合
- **API接続エラー**: e-Gov APIへの接続に失敗した場合
- **HTTPエラー**: APIからエラーレスポンスが返された場合

### エラーレスポンスの例

```
Error: limit must be between 1 and 100
Network Error: Failed to connect to API (ConnectTimeout)
API Error 404: Failed to retrieve law data
```

## 制限事項

1. **レート制限**: e-Gov APIのレート制限に準拠
2. **データ範囲**: e-Gov法令検索で公開されている法令のみ
3. **形式**: JSON/XML形式での取得のみサポート
4. **キャッシュの一貫性**: LRUキャッシュはプロセスローカルであり、Databricks Appsが複数レプリカで稼働する場合はレプリカ間でキャッシュ内容が一致しないことがある（機能上の問題はない）

## トラブルシューティング

### MCPサーバーに接続できない

- Unity AI Gatewayで本MCPサーバーが正しく登録されているか確認する
- 対象サービングエンドポイント（サービスプリンシパル）にUnity Catalogの `USE` 権限が付与されているか確認する
- Databricks Apps自体が起動しているか（Apps UIのステータス）を確認する。起動エラーの調査手順は [DEVELOPMENT.md](DEVELOPMENT.md) のトラブルシューティング節を参照

### 依存関係の問題（ローカル開発時）

```bash
uv sync --reinstall
```

## よくある質問

**Q: 法令番号がわからない場合はどうすればよいですか？**
A: まず `search_laws` で法令名を検索し、結果から法令番号を取得してください。

**Q: 大量のデータを取得したい場合は？**
A: `offset` と `limit` パラメータを使用してページネーションを実装してください。

**Q: XML形式とJSON形式の違いは？**
A: JSON形式は構造化されており解析しやすく、XML形式は元の法令構造により近い形式です。

**Q: APIのレート制限はありますか？**
A: e-Gov APIの利用規約に従ってください。過度なリクエストは避けてください。

**Q: Claude Desktopからも使えますか？**
A: `stdio` transportも維持されているため、従来通りClaude Desktopから `uv run e-gov-law-mcp` で起動して利用できます。
