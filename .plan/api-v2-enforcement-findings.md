# e-Gov 法令API v2 施行情報まわり 実地検証メモ（2026-07-06）

目的: 「法律がいつ施行されたか」の最新情報取得を最優先で実装するための、API v2実仕様の裏取り。

## OpenAPI spec の場所
- `GET /api/2/redoc` の HTML 内 `spec-url="/api/2/swagger-ui/lawapi-v2.yaml"`
- 実体: `https://laws.e-gov.go.jp/api/2/swagger-ui/lawapi-v2.yaml`（約126KB）
- `openapi.json` / `swagger.json` は 404。

## エンドポイント一覧（v2）
- `/laws` … 法令一覧・検索
- `/law_revisions/{law_id_or_num}` … 改正履歴（施行タイムライン）★施行情報の中核
- `/law_data/{law_id_or_num_or_revision_id}` … 本文取得
- `/attachment/{law_revision_id}` … 添付
- `/keyword` … 全文キーワード検索
- `/law_file/{file_type}/{law_id_or_num_or_revision_id}` … ファイル取得

## ★重要: パラメータ名はエンドポイントごとに違う（GPT/Claudeで割れた点の決着）
### /law_revisions/{id} のクエリ（施行日フィルタはここ）
- `amendment_date_from` … 改正法令**施行期日**（指定値含む、それ以後）例 `2024-06-07`
- `amendment_date_to` … 改正法令施行期日（指定値含む、それ以前）
- `amendment_promulgate_date_from` / `_to` … 公布日レンジ
- `current_revision_status` … 履歴の状態（複数可, カンマ区切り）※asofに関わらず常に現時点の状態と比較
- `mission` … `New`（新規制定/被改正）・`Partial`（一部改正）複数可 `New,Partial`
- `repeal_date_from` / `_to`, `repeal_status`

### /laws のクエリ（施行日レンジフィルタは**無い**）
- `asof=YYYY-MM-DD`（時点指定）, `mission`, `promulgation_date_from/to`（公布日のみ）,
  `repeal_status`, `omit_current_revision_info`
- → **施行日で全法令を横断フィルタする直接手段は /laws には無い**。施行日ベースは /law_revisions（法令個別）が担う。

## current_revision_status の enum（確定・4値）
- `CurrentEnforced` … 現行施行中
- `UnEnforced` … 未施行（これから施行される改正）
- `PreviousEnforced` … 施行済みだが現行ではない（過去版）
- `Repeal` … 廃止
（repeal_status 側は None / Repeal / Expire / LossOfEffectiveness）

## レスポンスの施行関連フィールド（revision_info / current_revision_info / revisions[]内 共通）
- `amendment_enforcement_date` … その版の**施行日**（YYYY-MM-DD）★これが「いつ施行されたか」
- `amendment_promulgate_date` … 改正法令の公布日
- `amendment_scheduled_enforcement_date` … 施行日が未確定（政令で定める日 等）のときの予定日
- `amendment_enforcement_comment` … 施行日の注記（例「公布の日から起算して三年を超えない範囲内において政令で定める日」）
- `amendment_law_id` / `amendment_law_title` / `amendment_law_num` … 改正法令
- `amendment_type` … 改正種別コード
- `mission` … New / Partial
- `current_revision_status` … 上記4値
- `law_revision_id` … 版ID（例 `129AC0000000089_20290623_508AC0000000045` = lawid_施行日_改正法令id）
- `current_revision_info` … asofに依存しない「現在以前の最新リビジョン」

## 実クエリ検証結果
1. `GET /laws?limit=1` → 200。total_count 9529。revision_info に施行フィールド実在確認。
2. `GET /law_revisions/129AC0000000089`（民法）→ 200。`revisions` に37版。降順。
   先頭=令和8年改正/施行2029-06-23/UnEnforced/「政令で定める日」。
3. `GET /law_revisions/129AC0000000089?current_revision_status=UnEnforced` → 未施行5版のみ抽出成功。
4. `GET /law_revisions/129AC0000000089?amendment_date_from=2020-01-01` → 2020以降施行の28版。
   UnEnforced(未来)→PreviousEnforced(過去) が施行日降順で混在。
5. `GET /laws?promulgation_date_from=2026-06-01` → 直近公布の法令一覧。各法にUnEnforced/CurrentEnforced判別可。

## 設計への含意（施行最新情報取得の最優先実装）
- 施行タイムラインは **/law_revisions/{id}** が本命。`current_revision_status` と `amendment_date_from/to` で
  「未施行」「直近施行済み」を切り分けられる。
- `law_revision_id` は `{lawid}_{施行日YYYYMMDD}_{改正法令id}` 構造 → 施行日が埋め込まれている。
- 「現在以前の最新」は current_revision_info、時点指定は asof（/laws, /law_data）。
- 施行日未確定改正は amendment_scheduled_enforcement_date / _comment で明示。確定扱いしないこと。
- /laws には施行日レンジフィルタが無いので、「全法令横断で直近施行を拾う」には
  公布日(promulgation_date_from)で候補を絞り→各法のrevisionを見る、等の合わせ技が要る。
