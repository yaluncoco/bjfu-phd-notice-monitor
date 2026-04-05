import json
import os
import re
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests

URL = "https://graduate.bjfu.edu.cn/zsgl/bszs/index.html"
STATE_FILE = Path("state.json")
TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://graduate.bjfu.edu.cn/",
}
LINK_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def fetch_html() -> str:
    resp = requests.get(URL, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
    return resp.text


def clean_html_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = unescape(text)
    text = " ".join(text.split())
    return text.strip()


def parse_items(html: str):
    items = []
    seen = set()
    for href, inner in LINK_RE.findall(html):
        text = clean_html_text(inner)
        if not text:
            continue
        full_text = text
        date_match = DATE_RE.search(full_text)
        if not date_match:
            continue
        date = date_match.group(1)
        title = full_text.replace(date, "").strip(" -–—|[]【】")
        if not title:
            continue
        link = urljoin(URL, unescape(href))
        if "/zsgl/bszs/" not in link or link.endswith("/index.html") or link.endswith("/index1.html"):
            continue
        key = (title, date, link)
        if key in seen:
            continue
        seen.add(key)
        items.append({"title": title, "date": date, "link": link})

    def sort_key(x):
        try:
            return datetime.strptime(x["date"], "%Y-%m-%d")
        except ValueError:
            return datetime.min

    items.sort(key=sort_key, reverse=True)
    return items


def load_state():
    if not STATE_FILE.exists():
        return {"items": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"items": []}


def save_state(items):
    payload = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "source": URL,
        "items": items,
    }
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def diff_new_items(old_items, new_items):
    old_keys = {(i.get("title"), i.get("date"), i.get("link")) for i in old_items}
    return [i for i in new_items if (i["title"], i["date"], i["link"]) not in old_keys]


def send_email(new_items):
    smtp_host = os.environ.get("SMTP_HOST", "smtp.163.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    email_to = os.environ["EMAIL_TO"]

    lines = ["北京林业大学博士招生通知有更新：", ""]
    for item in new_items:
        lines.append(f"- {item['date']} | {item['title']}")
        lines.append(f"  {item['link']}")
    lines.append("")
    lines.append(f"来源：{URL}")
    body = "\n".join(lines)

    subject = f"[BJFU博士招生通知] 新增 {len(new_items)} 条"
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = email_to

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [email_to], msg.as_string())


def main():
    html = fetch_html()
    latest_items = parse_items(html)
    if not latest_items:
        raise RuntimeError("未解析到任何通知，可能是页面结构变化。")

    state = load_state()
    old_items = state.get("items", [])
    new_items = diff_new_items(old_items, latest_items)

    print(f"parsed={len(latest_items)} old={len(old_items)} new={len(new_items)}")
    for item in new_items[:10]:
        print(f"NEW {item['date']} {item['title']} -> {item['link']}")

    if old_items and new_items:
        send_email(new_items)
        print("已发送邮件通知")
    elif not old_items:
        print("首次运行：仅初始化 state.json，不发送邮件，避免把历史通知全部当作新增。")
    else:
        print("没有新增通知")

    save_state(latest_items)


if __name__ == "__main__":
    main()
