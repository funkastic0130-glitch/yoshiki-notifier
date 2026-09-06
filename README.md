# YOSHIKI Yahoo!ニュース通知システム

「YOSHIKI」に関する記事がYahoo!ニュースに掲載されたら、LINEとWhatsAppの両方に通知するシステムです。
GitHub Actionsで30分おきに自動チェックします（サーバー不要・基本無料）。

## 仕組み

- Yahoo!ニュース自体にはキーワード検索RSSが無いため、**Googleニュースの検索RSSに`site:news.yahoo.co.jp`を組み合わせて**Yahoo!ニュース内の記事だけを抽出しています。
- 一度通知した記事のURLは`seen.json`に記録し、重複通知を防ぎます。
- 初回実行時は、その時点の既存記事をまとめて通知すると大量になってしまうため、**初回だけは通知せず記録のみ**行います（2回目以降のチェックから通知されます）。

---

## セットアップ手順

### 1. このリポジトリをGitHubにアップロード

1. GitHubで新しいリポジトリを作成（Public/Privateどちらでも可。Privateの場合もGitHub Actionsは無料枠内で使えます）
2. このフォルダの中身（`check_news.py`, `requirements.txt`, `.github/workflows/check_news.yml`）をリポジトリにpush

### 2. LINE通知の準備（LINE Messaging API）

LINE Notifyは2025年3月末で終了したため、LINE公式アカウント経由の「Messaging API」を使います。

1. [LINE Developers](https://developers.line.biz/ja/) にログイン（LINEアカウントでOK）
2. 「プロバイダー」を新規作成
3. そのプロバイダー配下に「Messaging API」チャネルを新規作成（＝自分専用のLINE公式アカウントができます）
4. チャネル作成後、以下を行う:
   - 「Messaging API設定」タブで **チャネルアクセストークン（長期）** を発行 → これが`LINE_CHANNEL_ACCESS_TOKEN`
   - 同タブに表示されるQRコードを**自分のLINEアプリで読み取り、この公式アカウントを友だち追加**する
   - 応答メッセージなどの自動応答はオフにしておいてOK（Messaging API設定 > 応答メッセージ をオフ）

> 補足: このスクリプトは「ブロードキャスト送信」を使っており、この公式アカウントの友だち全員に送信します。自分しか友だち追加していなければ、実質的に自分だけに届きます。ユーザーIDを個別に取得する必要はありません。
>
> 無料枠は月200通までです。それを超える場合は有料プランが必要になります。

### 3. WhatsApp通知の準備（Twilio）

1. [Twilio](https://www.twilio.com/) で無料アカウントを作成（無料トライアルクレジットあり）
2. コンソール左側メニューから **Messaging > Try it out > Send a WhatsApp message** を開く
3. 表示されるサンドボックス番号（例: `+1 415 523 8886`）に、指定された合言葉（例: `join xxxx-xxxx`）を**自分のWhatsAppから送信**して、サンドボックスに参加する
4. Twilioコンソールのダッシュボードから **Account SID** と **Auth Token** を取得
5. 環境変数に設定する値:
   - `TWILIO_ACCOUNT_SID` : Account SID
   - `TWILIO_AUTH_TOKEN` : Auth Token
   - `TWILIO_WHATSAPP_FROM` : `whatsapp:+14155238886`（サンドボックス番号。実際に表示された番号を使う）
   - `WHATSAPP_TO` : `whatsapp:+819012345678`（自分の番号。国番号付き、サンドボックスに参加済みの番号）

> 注意: これはあくまで**サンドボックス（テスト用）**です。トライアルアカウントの制限として、
> - サンドボックスに参加した番号にしか送れない
> - メッセージ冒頭に「Sent from Twilio trial account」のような注記が付く
> - 一定期間参加しないとサンドボックスから外れる場合がある
>
> 本格的な運用（自分専用の番号・注記なし）には、WhatsApp Business APIの申請と有料プランへの移行が必要です。個人利用の通知目的であれば、まずはサンドボックスで十分動作します。

### 4. GitHubリポジトリにSecretsを登録

リポジトリの **Settings > Secrets and variables > Actions > New repository secret** から、以下を登録:

| Secret名 | 値 |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | 手順2で取得したトークン |
| `TWILIO_ACCOUNT_SID` | 手順3で取得したSID |
| `TWILIO_AUTH_TOKEN` | 手順3で取得したトークン |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` など |
| `WHATSAPP_TO` | `whatsapp:+819012345678` など |

LINEだけ、WhatsAppだけ使いたい場合は、使わない方のSecretsを設定しなければ、そちらへの送信は自動的にスキップされます（エラーにはなりません）。

### 5. 動作確認

1. リポジトリの **Actions** タブを開く
2. 「Check YOSHIKI Yahoo News」ワークフローを選択し、**Run workflow** で手動実行
3. ログを確認（初回は「初回実行のため通知はスキップし〜」と出て`seen.json`が作られるはず）
4. もう一度手動実行して、新着があれば通知が届くことを確認
   - 動作確認のため一時的に`seen.json`の中身を空配列 `[]` にしてpushすると、既存記事が「新着」扱いになり通知テストができます

---

## カスタマイズ

- **キーワードを変える**: `check_news.py` の `SEARCH_KEYWORD = "YOSHIKI"` を変更
- **チェック頻度を変える**: `.github/workflows/check_news.yml` の `cron: "*/30 * * * *"` を変更（例: 15分毎なら `*/15 * * * *`）
- **通知文言を変える**: `check_news.py` 内の `message = f"【YOSHIKI ニュース】..."` を変更

## 制限事項

- GitHub ActionsのスケジュールCronは、混雑状況により実際の実行が数分〜十数分遅れることがあります（リアルタイム性が必須の場合は不向き）
- Googleニュース経由のため、Yahoo!ニュースに掲載されてからGoogleにインデックスされるまでのタイムラグが多少発生します
- LINEは月200通、Twilioサンドボックスは試用目的である点に注意してください
