"""
YOSHIKIに関するYahoo!ニュース記事を監視し、新着があればLINE / WhatsAppに通知するスクリプト。

仕組み:
- Yahoo!ニュース自体にはキーワード検索RSSが無いため、Googleニュースの検索RSSに
  「site:news.yahoo.co.jp」を組み合わせて、Yahoo!ニュース内の記事だけを抽出する。
- 一度通知した記事のURLは seen.json に保存し、次回以降は重複通知しないようにする。
- 初回実行時は「その時点で存在する記事」を全部通知すると大量になるため、
  初回はseen.jsonの初期化のみ行い、通知は送らない。

環境変数（GitHub Actionsのsecretsから渡す想定）:
- LINE_CHANNEL_ACCESS_TOKEN : LINE Messaging APIのチャネルアクセストークン
- TWILIO_ACCOUNT_SID        : TwilioのAccount SID
- TWILIO_AUTH_TOKEN         : TwilioのAuth Token
- TWILIO_WHATSAPP_FROM      : 送信元WhatsApp番号 (例: "whatsapp:+14155238886")
- WHATSAPP_TO               : 送信先WhatsApp番号 (例: "whatsapp:+819012345678")

いずれの通知も、対応する環境変数が未設定ならスキップされる（エラーにはならない）。
"""

import os
import json
import feedparser
import requests

# 検索キーワード（変更したい場合はここを書き換える）
SEARCH_KEYWORD = "YOSHIKI"

RSS_URL = (
    "https://news.google.com/rss/search?q="
    f"{SEARCH_KEYWORD}+site:news.yahoo.co.jp&hl=ja&gl=JP&ceid=JP:ja"
)

STATE_FILE = "seen.json"

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
WHATSAPP_TO = os.environ.get("WHATSAPP_TO")


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def fetch_articles():
    feed = feedparser.parse(RSS_URL)
    articles = []
    for entry in feed.entries:
        link = entry.get("link")
        title = entry.get("title")
        if link and title:
            articles.append({"link": link, "title": title})
    return articles


def send_line(message: str):
    """LINE公式アカウントの友だち全員（=自分）にブロードキャスト送信する。
    個別のユーザーIDを取得する手間を省くため、pushではなくbroadcastを使う。
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("[LINE] LINE_CHANNEL_ACCESS_TOKEN が未設定のためスキップします")
        return

    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {"messages": [{"type": "text", "text": message}]}

    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.status_code != 200:
        print(f"[LINE] 送信失敗: {resp.status_code} {resp.text}")
    else:
        print("[LINE] 送信成功")


def send_whatsapp(message: str):
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM and WHATSAPP_TO):
        print("[WhatsApp] Twilio関連の環境変数が未設定のためスキップします")
        return

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = {
        "From": TWILIO_WHATSAPP_FROM,
        "To": WHATSAPP_TO,
        "Body": message,
    }
    resp = requests.post(
        url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=10
    )
    if resp.status_code not in (200, 201):
        print(f"[WhatsApp] 送信失敗: {resp.status_code} {resp.text}")
    else:
        print("[WhatsApp] 送信成功")


def main():
    state_exists = os.path.exists(STATE_FILE)
    seen = load_seen()
    articles = fetch_articles()
    print(f"取得した記事数: {len(articles)}")

    if not state_exists:
        # 初回実行: 既存記事を全部「既読」として記録するだけで、通知はしない
        for a in articles:
            seen.add(a["link"])
        save_seen(seen)
        print(f"初回実行のため通知はスキップし、{len(seen)}件を既読として記録しました。")
        return

    new_articles = [a for a in articles if a["link"] not in seen]

    if not new_articles:
        print("新着記事はありませんでした。")
        return

    # 古い順に通知（フィードは新しい順に並んでいることが多いためreverse）
    for article in reversed(new_articles):
        message = f"【YOSHIKI ニュース】\n{article['title']}\n{article['link']}"
        send_line(message)
        send_whatsapp(message)
        seen.add(article["link"])

    save_seen(seen)
    print(f"{len(new_articles)}件の新着記事を通知しました。")


if __name__ == "__main__":
    main()
