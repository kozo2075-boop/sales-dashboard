import re
import json
import time
import random
import socket
import sqlite3
from datetime import datetime
from pathlib import Path
from io import BytesIO
import io

import pandas as pd
import numpy as np
import streamlit as st
import requests
from bs4 import BeautifulSoup

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

# =============================
# Streamlit config
# =============================
st.set_page_config(
    page_title="Sales Intelligence (MyFans / CandFans)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================
# THEME (ダーク＋ネオン)
# =============================
st.markdown(
    """
<style>
:root{
  --bg: #070915;
  --panel: rgba(255,255,255,0.06);
  --panel2: rgba(255,255,255,0.04);
  --border: rgba(255,255,255,0.12);
  --text: #EAF0FF;
  --muted: rgba(234,240,255,0.70);

  --c-cyan:   #39F8FF;
  --c-purple: #B46CFF;
  --c-pink:   #FF49D7;
  --c-yellow: #FFF14D;
  --c-green:  #39FF7A;
  --c-blue:   #3AA8FF;
}

html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main{
  background:
    radial-gradient(1200px 800px at 55% -10%, rgba(180,108,255,0.26), transparent 58%),
    radial-gradient(900px 700px at 18% 25%, rgba(57,248,255,0.16), transparent 62%),
    radial-gradient(900px 700px at 88% 70%, rgba(255,73,215,0.12), transparent 62%),
    var(--bg) !important;
  color: var(--text) !important;
}

[data-testid="stHeader"]{ background: transparent !important; }
[data-testid="stToolbar"]{ right: 0.75rem !important; }

section[data-testid="stSidebar"]{
  background:
    linear-gradient(180deg, rgba(180,108,255,0.10), rgba(57,248,255,0.04)),
    rgba(7,9,21,0.98) !important;
  border-right: 1px solid rgba(255,255,255,0.12);
}

/* サイドバー透け対策：完全不透過 */
section[data-testid="stSidebar"]{
  backdrop-filter: none !important;
}

.block-container{
  padding-top: 1.0rem;
  padding-bottom: 2.0rem;
  max-width: 1280px;
}

.card{
  background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 18px 50px rgba(0,0,0,0.50);
}

.cardGlow{
  border: 1px solid rgba(180,108,255,0.28);
  box-shadow:
    0 18px 70px rgba(180,108,255,0.16),
    0 0 0 1px rgba(57,248,255,0.10) inset;
}

.h1{
  font-size: 1.9rem; font-weight: 950; letter-spacing: 0.2px;
}
.muted{ color: var(--muted) !important; }

.badge{
  display:inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(180,108,255,0.45);
  background: rgba(180,108,255,0.16);
  color: var(--text);
  font-size: 0.82rem;
  white-space: nowrap;
}

.hr{
  height: 1px;
  background: rgba(255,255,255,0.12);
  margin: 12px 0 10px 0;
}

.stButton>button{
  border-radius: 14px;
  padding: .58rem .95rem;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(180,108,255,0.20);
}
.stButton>button:hover{
  border: 1px solid rgba(180,108,255,0.70);
  background: rgba(180,108,255,0.30);
}

button[data-baseweb="tab"]{
  border-radius: 14px !important;
  margin-right: 6px !important;
}
button[data-baseweb="tab"][aria-selected="true"]{
  background: rgba(180,108,255,0.24) !important;
  border: 1px solid rgba(180,108,255,0.40) !important;
}

div[data-testid="stDataFrame"] {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.03);
}

@media (max-width: 640px) {
  .block-container {padding-left: 0.8rem; padding-right: 0.8rem;}
  .h1{font-size: 1.55rem;}
}
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# Colors (最新要望に合わせる)
# =============================
COLORS = {
    # =========================
    # ALL
    # =========================
    # 折れ線（ALL）
    "ALL_LINE": "#4EF282",  # ネオングリーン

    # =========================
    # MyFans
    # =========================
    # 円グラフ（売上割合・大 → 小）
    "MY_PIE": [
        "#B22222",  # 赤
        "#FF5E5E",  # 赤 → オレンジ
        "#FFC0CB",  # オレンジ
        "#FFD1C1",
        "#FFE6D6",
    ],

    # プラン名 → 固定色（円グラフ用）
    "MY_PLAN_COLORS": {
        "顔出し最強プラン": "#B22222",
        "こた倶楽部": "#FF5E5E",
        "バックナンバー": "#FFC0CB",
        "バックナンバー(単月)": "#FFE1E8",
    },

    # 棒グラフ（投稿TOPなど）
    "MY_BAR": "#FA6B6B",
    "MY_POST_BAR": "#FA6B6B",   # 投稿用（エラー回避）
    "MY_PLAN_BAR": "#FA6B6B",  # プラン用（将来用）
    "MY_PLAN_BASE": "#FF0000",  # MyFansプラン円グラフの基本色（濃い赤）

    # 折れ線（MyFans 単体がある場合用）
    "MY_LINE": "#FF2B2B",

    # =========================
    # CandFans
    # =========================
    # 円グラフ（売上割合・大 → 小）
    "CA_PIE": [
        "#9900FF",
        "#C059FB",
        "#EAB7F7",
    ],

    # プラン名 → 固定色（円グラフ用）
    "CA_PLAN_COLORS": {
        "顔出し最強プラン": "#9900FF",
        "こた倶楽部": "#C059FB",
        "バックナンバー": "#EAB7F7",
    },

    # 棒グラフ
    "CA_BAR": "#BF66FF",
    "CA_POST_BAR": "#BF66FF",   # 投稿用（エラー回避）
    "CA_PLAN_BAR": "#BF66FF",   # プラン用（将来用）
    "CA_PLAN_BASE": "#380061",  # CandFansプラン円グラフの基本色（濃い紫）


    # 折れ線
    "CA_LINE": "#AA2BFF",

    # =========================
    # 共通
    # =========================
    # 円グラフの枠線
    "PIE_EDGE": "#696969",
}


# =============================
# Storage
# =============================
BASE_DIR = Path("uploads")
MY_DIR = BASE_DIR / "myfans"
CAND_RAW_DIR = BASE_DIR / "candfans_raw"
for p in [MY_DIR, CAND_RAW_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# =============================
# Admin mode
# =============================
ADMIN_PIN = "1234"  # 好きに変更OK

st.sidebar.markdown("### 🔐 モード切替")
admin_toggle = st.sidebar.toggle("管理者モードを有効にする", value=False)

is_admin = False
if admin_toggle:
    pin = st.sidebar.text_input("PIN", type="password")
    if pin == ADMIN_PIN:
        is_admin = True
        st.sidebar.success("管理者 ON（アップロード可能）")
    else:
        st.sidebar.warning("PINが違います")
else:
    st.sidebar.markdown("### 👀 閲覧モード（スマホ推奨）")
    st.sidebar.caption("アップロードはPCで / スマホは閲覧のみ")

# スマホ表示モード（手動）
st.sidebar.markdown("### 📱 表示")
mobile_mode = st.sidebar.toggle("スマホ表示モード（縦並び/小さめ）", value=False)

# =============================
# Utility
# =============================
def normalize_spaces(text: str) -> str:
    return " ".join(str(text).split())

def first_sentence(text: str) -> str:
    if not text:
        return ""
    t = normalize_spaces(text)
    for sep in ["。", "！", "!", "？", "?", "…", "\n"]:
        p = t.find(sep)
        if p != -1:
            t = t[:p]
            break
    return t.strip()

def clip_text(text: str, max_len: int = 26) -> str:
    if not text:
        return ""
    t = text.strip()
    return t if len(t) <= max_len else t[: max_len - 1] + "…"

def summarize_title(raw: str, max_len: int) -> str:
    if not raw:
        return ""
    t = first_sentence(raw)
    t = normalize_spaces(t)
    t = re.sub(r"[💓💗💖💘💕❤️💙💚💛💜🧡💎⭐️✨🔥]+", "", t)
    t = re.sub(r"[【】\[\]（）\(\)]+", "", t)
    t = re.sub(r"[・|｜]+", " ", t)
    t = normalize_spaces(t).strip()
    return clip_text(t, max_len=max_len)


# -----------------------------
# Number formatting (display)
# -----------------------------
def fmt_yen(v) -> str:
    """Format number as Japanese Yen string with commas."""
    try:
        x = float(v) if v is not None and v != "" else 0.0
    except Exception:
        x = 0.0
    return f"¥{x:,.0f}"

def fmt_pct(p) -> str:
    """Format percentage (already in 0..100 scale) with 1 decimal."""
    try:
        x = float(p) if p is not None and p != "" else 0.0
    except Exception:
        x = 0.0
    return f"{x:.1f}%"

def parse_year_month_from_name(name: str):
    m = re.search(r"(20\d{2})[-_/](\d{2})", name)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"

def parse_jp_md_hms(s: str, year: int):
    s = str(s).strip()
    m = re.match(r"(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{2}):(\d{2})", s)
    if not m:
        return pd.NaT
    month, day, hh, mm, ss = map(int, m.groups())
    return pd.Timestamp(year=year, month=month, day=day, hour=hh, minute=mm, second=ss)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def safe_read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp932")

# =============================
# Title cache (MyFans URL -> Title)
# =============================
DB_PATH = "title_cache.sqlite3"
con = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = con.cursor()
cur.execute(
    """
CREATE TABLE IF NOT EXISTS title_cache (
  url TEXT PRIMARY KEY,
  title TEXT,
  fetched_at TEXT
)
"""
)
con.commit()

def get_cached_title(url: str):
    c = con.cursor()
    c.execute("SELECT title FROM title_cache WHERE url=?", (url,))
    row = c.fetchone()
    return row[0] if row else None

def set_cached_title(url: str, title: str):
    c = con.cursor()
    c.execute(
        "INSERT OR REPLACE INTO title_cache(url, title, fetched_at) VALUES (?, ?, ?)",
        (url, title, datetime.now().isoformat(timespec="seconds")),
    )
    con.commit()

# --- compat alias (古い関数名で呼ばれても落ちないようにする) ---
def get_title_cache(url: str):
    return get_cached_title(url)

def set_title_cache(url: str, title: str):
    return set_cached_title(url, title)


# =============================
# HTTP session + fetch
# =============================
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
)

def fetch_title_from_web(url: str, timeout=12, max_retries=2):
    """
    1) og:description / description の1文目
    2) og:title
    3) <title>
    """
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            r = SESSION.get(url, timeout=timeout, allow_redirects=True)
            status = r.status_code
            if status in (403, 429):
                raise RuntimeError(f"Blocked (HTTP {status})")
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")

            def meta(name=None, prop=None):
                if prop:
                    m = soup.find("meta", attrs={"property": prop})
                else:
                    m = soup.find("meta", attrs={"name": name})
                return m.get("content").strip() if m and m.get("content") else None

            desc = meta(prop="og:description") or meta(name="description")
            if desc:
                t = first_sentence(desc)
                if t:
                    return t

            ogt = meta(prop="og:title")
            if ogt:
                t = first_sentence(ogt)
                if t:
                    return t

            if soup.title and soup.title.string:
                t = first_sentence(soup.title.string.strip())
                if t:
                    return t

            raise RuntimeError("No title/description found")

        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(1.0 + attempt * 1.2)
                continue
            raise last_err
def gather_myfans_urls_all_period() -> list[str]:
    """
    uploads/myfans に保存済みの myfans_YYYY-MM.csv を全て読み、
    対象URL から http(s) のURLだけをユニークで返す
    """
    urls: set[str] = set()

    if not MY_DIR.exists():
        return []

    for p in sorted(MY_DIR.glob("myfans_*.csv")):
        try:
            df = pd.read_csv(p)
        except Exception:
            continue

        col = None
        if "対象URL" in df.columns:
            col = "対象URL"
        elif "url" in df.columns:
            col = "url"

        if col is None:
            continue

        ser = df[col].dropna().astype(str)
        for u in ser:
            u = u.strip()
            if u.startswith("http://") or u.startswith("https://"):
                urls.add(u)

    return sorted(urls)

def gather_myfans_urls_per_month(topn_per_month: int = 10) -> list[str]:
    """
    uploads/myfans の myfans_YYYY-MM.csv を月ごとに読み、
    post（単品）の金額が大きい順に topn_per_month 件だけURLを集めて返す（ユニーク）
    """
    urls: list[str] = []

    if not MY_DIR.exists():
        return []

    topn_per_month = int(topn_per_month) if topn_per_month else 0
    if topn_per_month <= 0:
        # 0以下なら従来どおり全期間（全URL）にフォールバック
        return gather_myfans_urls_all_period()

    for p in sorted(MY_DIR.glob("myfans_*.csv")):
        try:
            df = safe_read_csv(p)
        except Exception:
            continue

        # 必要カラム（MyFans CSV 前提）
        need = ["種類", "金額", "対象URL"]
        if any(c not in df.columns for c in need):
            continue

        d = df.copy()
        d["種類"] = d["種類"].astype(str)
        d = d[d["種類"].str.contains("単品", na=False)]  # post相当
        if len(d) == 0:
            continue

        d["amount"] = pd.to_numeric(d["金額"], errors="coerce").fillna(0)
        d["url"] = d["対象URL"].astype(str).fillna("").str.strip()

        d = d[(d["url"].str.startswith("http://")) | (d["url"].str.startswith("https://"))]
        if len(d) == 0:
            continue

        d = d.sort_values("amount", ascending=False).head(topn_per_month)
        urls.extend(d["url"].tolist())

    # 月ごとに集めたものをユニーク化（順序は維持）
    seen = set()
    uniq = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def bulk_fetch_myfans_titles_all_period(
        limit: int | None = None,
        per_month_topn: int | None = None,
        timeout: int = 12,
        min_wait: float = 4.0,
        max_wait: float = 8.0,
        retries: int = 2,
    ) -> tuple[int, int]:
        """
        全期間のURLを対象にタイトルを取得してキャッシュへ保存
        - per_month_topn が指定されていれば「各月 topN URL」から取得
        - limit があれば最終的な対象数を上限でカット

        戻り値: (対象URL数, 更新できた数)
        """
        if per_month_topn is not None and int(per_month_topn) > 0:
            urls = gather_myfans_urls_per_month(int(per_month_topn))
        else:
            urls = gather_myfans_urls_all_period()

        if limit is not None and int(limit) > 0:
            urls = urls[: int(limit)]

        updated = 0
        for url in urls:
            cached = get_cached_title(url)
            if cached:
                continue

            # 取得（失敗しても落とさない）
            try:
                title = fetch_title_from_web(url, timeout=timeout, max_retries=retries)
            except Exception:
                title = None

            if title:
                set_cached_title(url, title)
                updated += 1

            # 間隔を空ける（ブロック回避）
            time.sleep(random.uniform(float(min_wait), float(max_wait)))

        return (len(urls), updated)



# =============================
# Load: MyFans (CSV)
# =============================
@st.cache_data(show_spinner=False)
def load_myfans_all(title_len: int) -> pd.DataFrame:
    rows = []
    for csv_path in sorted(MY_DIR.glob("*.csv")):
        ym = parse_year_month_from_name(csv_path.stem) or parse_year_month_from_name(csv_path.name)
        if not ym:
            continue
        year = int(ym.split("-")[0])

        df_raw = safe_read_csv(csv_path)

        required = ["日付", "金額", "手数料", "種類", "対象", "対象URL"]
        if any(c not in df_raw.columns for c in required):
            continue

        def classify_item_type(kind: str, url: str = "") -> str:
            kind_s = "" if pd.isna(kind) else str(kind)
            url_s = "" if pd.isna(url) else str(url)
            u = url_s.lower()
            # バックナンバー（単月含む）はプラン扱い（MyFans固有）
            if "backnumber" in u or "バックナンバー" in kind_s:
                return "plan"
            # URL優先: /account/plans/ や /plans/ はプラン購入扱い
            if "/account/plans/" in u or "/plans/" in u:
                return "plan"
            # 投稿URLは post 扱い
            if "/posts/" in u or "/post/" in u:
                return "post"
            # 種類テキストで判定
            if "プラン" in kind_s or "定期" in kind_s or "サブスク" in kind_s or "月額" in kind_s:
                return "plan"
            if "単品" in kind_s or "投稿" in kind_s:
                return "post"
            # 不明な場合は post として扱う（表示が欠けないように）
            return "post"

        for _, r in df_raw.iterrows():
            occurred = parse_jp_md_hms(r["日付"], year)
            amount = pd.to_numeric(r["金額"], errors="coerce")
            fee = pd.to_numeric(r["手数料"], errors="coerce")
            url = str(r["対象URL"]) if not pd.isna(r["対象URL"]) else ""
            item_type = classify_item_type(r["種類"], url)

            if item_type == "plan":
                kind_s = "" if pd.isna(r["種類"]) else str(r["種類"])
                if "バックナンバー" in kind_s:
                    if ("単月" in kind_s) or ("1ヶ月" in kind_s) or ("１ヶ月" in kind_s):
                        raw_title = "バックナンバー(単月)"
                    else:
                        raw_title = "バックナンバー"
                else:
                    raw_title = str(r["対象"]) if not pd.isna(r["対象"]) else ""
                title_short = summarize_title(raw_title, int(title_len))
            else:
                cached = get_cached_title(url) if url else None
                raw_title = cached if cached else ""
                title_short = summarize_title(raw_title, int(title_len)) if raw_title else ""

            rows.append(
                {
                    "platform": "myfans",
                    "year_month": ym,
                    "occurred_at": occurred,
                    "amount": float(amount) if pd.notna(amount) else 0.0,
                    "fee": float(fee) if pd.notna(fee) else 0.0,
                    "item_type": item_type,
                    "title_raw": raw_title,
                    "title_short": title_short,
                    "url": url,
                }
            )

    # rows -> DataFrame
    if not rows:
        return pd.DataFrame(
            columns=[
                "platform",
                "year_month",
                "occurred_at",
                "amount",
                "fee",
                "item_type",
                "title_raw",
                "title_short",
                "url",
            ]
        )

    df = pd.DataFrame(rows)
    # 型整形
    df["occurred_at"] = pd.to_datetime(df["occurred_at"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["fee"] = pd.to_numeric(df["fee"], errors="coerce").fillna(0.0)
    df["year_month"] = df["year_month"].astype(str)
    df["item_type"] = df["item_type"].astype(str)
    df["title_raw"] = df["title_raw"].astype(str)
    df["title_short"] = df["title_short"].astype(str)
    df["url"] = df["url"].astype(str)
    return df


# =============================
# Load: CandFans (CSV/JSON)
# =============================
def infer_cand_item_type(filename: str):
    fn = str(filename)
    if re.search(r"(plan|プラン)", fn, flags=re.IGNORECASE):
        return "plan"
    if re.search(r"(post|投稿|単品)", fn, flags=re.IGNORECASE):
        return "post"
    return "unknown"

def _parse_cand_csv_date(s):
    """
    Cand CSV の phone 列が '2026.01.31' 形式の想定
    """
    s = str(s).strip()
    if not s:
        return pd.NaT
    # 2026.01.31 / 2026-01-31 なども一応許容
    s = s.replace("/", ".").replace("-", ".")
    try:
        return pd.to_datetime(s, format="%Y.%m.%d", errors="coerce")
    except Exception:
        return pd.to_datetime(s, errors="coerce")

def _parse_cand_amount(x):
    """
    data3 が '1,483' の想定
    """
    if pd.isna(x):
        return 0.0
    s = str(x).strip()
    s = s.replace(",", "")
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s) if s else 0.0
    except Exception:
        return 0.0

@st.cache_data(show_spinner=False)
def load_candfans_all(title_len: int) -> pd.DataFrame:
    rows = []

    # ---------- 1) JSON（従来どおり） ----------
    for path in sorted(CAND_RAW_DIR.glob("*.json")):
        item_type_from_name = infer_cand_item_type(path.name)

        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue

        histories = data.get("histories", [])
        if isinstance(histories, dict):
            histories = list(histories.values())

        for h in histories:
            order = h.get("order", {}) or {}
            item = h.get("item", {}) or {}

            occurred = pd.to_datetime(order.get("sales_date"), errors="coerce")
            ym = occurred.strftime("%Y-%m") if pd.notna(occurred) else (parse_year_month_from_name(path.name) or "unknown")

            amount = float(order.get("amount", 0) or 0)

            raw_title = item.get("name") or item.get("title") or ""
            short = summarize_title(raw_title, int(title_len)) if raw_title else ""

            rows.append(
                {
                    "platform": "candfans",
                    "year_month": ym,
                    "dedupe_key": f'{order.get("orders_id","")}_{order.get("sales_date","")}_{order.get("amount","")}_{item.get("id","")}_{item_type_from_name}',
                    "occurred_at": occurred,
                    "amount": amount,
                    "fee": 0.0,
                    "item_type": item_type_from_name,
                    "title_raw": raw_title,
                    "title_short": short,
                    "url": "",
                }
            )

    # ---------- 2) CSV（新対応） ----------
    for path in sorted(CAND_RAW_DIR.glob("*.csv")):
        item_type_from_name = infer_cand_item_type(path.name)

        try:
            df_raw = safe_read_csv(path)
        except Exception:
            continue

        # 想定カラム（あなたが添付してくれたCSV形式）
        # data  : タイトル（プラン名/作品名）
        # data2 : IDっぽい（重複排除のキーに使う）
        # data3 : 金額（カンマあり）
        # phone : 日付（YYYY.MM.DD）
        need = ["data", "data2", "data3", "phone"]
        if any(c not in df_raw.columns for c in need):
            # 形式が違うCSVだったらスキップ（必要ならここを拡張）
            continue

        for _, r in df_raw.iterrows():
            occurred = _parse_cand_csv_date(r.get("phone"))
            ym = occurred.strftime("%Y-%m") if pd.notna(occurred) else (parse_year_month_from_name(path.name) or "unknown")

            amount = _parse_cand_amount(r.get("data3"))

            raw_title = str(r.get("data") or "").strip()
            short = summarize_title(raw_title, int(title_len)) if raw_title else ""

            # 重複排除（同一行の再アップロード対策）
            rid = str(r.get("data2") or "").strip()
            dkey = f"csv_{rid}_{str(r.get('phone') or '')}_{str(r.get('data3') or '')}_{item_type_from_name}"

            rows.append(
                {
                    "platform": "candfans",
                    "year_month": ym,
                    "dedupe_key": dkey,
                    "occurred_at": occurred,
                    "amount": float(amount),
                    "fee": 0.0,
                    "item_type": item_type_from_name,
                    "title_raw": raw_title,
                    "title_short": short,
                    "url": "",
                }
            )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["occurred_at"] = pd.to_datetime(df["occurred_at"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["fee"] = pd.to_numeric(df["fee"], errors="coerce").fillna(0)

    # dedupe_key がある場合は重複排除して消す（従来と同じ）
    if "dedupe_key" in df.columns:
        df = df.drop_duplicates(subset=["dedupe_key"], keep="first")
        df = df.drop(columns=["dedupe_key"], errors="ignore")

    return df

# =============================
# Sidebar: Access URLs（管理者URLも表示）
# =============================
st.sidebar.markdown("### 🌐 アクセス先")
ip = get_local_ip()
st.sidebar.code("Local:   http://localhost:8501")
if ip:
    st.sidebar.code(f"Network: http://{ip}:8501")
st.sidebar.code("Admin:   上のURL末尾に ?mode=admin を付ける")
st.sidebar.caption("例: http://localhost:8501/?mode=admin")

# =============================
# Sidebar: Settings
# =============================
st.sidebar.markdown("### ⚙️ 設定")
title_len = st.sidebar.slider("要約タイトルの長さ", 10, 40, 26, 1)

# =============================
# Admin upload area
# =============================
if is_admin:
    st.sidebar.markdown("### ⬆️ データアップロード（管理者）")

    st.sidebar.markdown("#### MyFans CSV")
    st.sidebar.caption("推奨：myfans_YYYY-MM.csv（自動で月に仕分け）")

    up_my = st.sidebar.file_uploader(
        "MyFans CSV",
        type=["csv"],
        key="up_my",
        accept_multiple_files=True,  # ★複数対応
    )
    my_ym = st.sidebar.text_input("保存する年月（YYYY-MM）※ファイル名に入ってない時だけ", value="")

    if up_my and st.sidebar.button("MyFans CSVを保存"):
        saved = 0
        errors = 0

        for fobj in up_my:
            ym = parse_year_month_from_name(Path(fobj.name).stem) or my_ym.strip()
            if not re.match(r"^20\d{2}-\d{2}$", ym):
                st.sidebar.error(f"年月が不正です: {fobj.name} → '{ym}'（例: 2026-01）")
                errors += 1
                continue

            out = MY_DIR / f"myfans_{ym}.csv"
            with open(out, "wb") as wf:
                wf.write(fobj.getbuffer())
            saved += 1

        if saved:
            st.sidebar.success(f"{saved}件 保存しました（{errors}件 スキップ）")
            try:
                st.cache_data.clear()
            except Exception:
                pass



    st.sidebar.markdown("#### CandFans（CSV/JSON）")
    st.sidebar.caption("plan/postはファイル名で判定（例：candfans_2026-01_plan.csv / candfans_2026-01_post.csv）")
    up_cand = st.sidebar.file_uploader(
        "CandFans CSV/JSON（複数OK）",
        type=["csv", "json"],
        accept_multiple_files=True,
        key="up_ca",
    )
    if up_cand and st.sidebar.button("CandFans を保存"):
        saved = 0
        for fobj in up_cand:
            out = CAND_RAW_DIR / fobj.name
            with open(out, "wb") as f:
                f.write(fobj.getbuffer())
            saved += 1
        st.sidebar.success(f"{saved} 件 保存しました")
        try:
            st.cache_data.clear()
        except Exception:
            pass

        saved = 0
        for jf in up_cand:
            out = CAND_RAW_DIR / jf.name
            with open(out, "wb") as f:
                f.write(jf.getbuffer())
            saved += 1
        st.sidebar.success(f"{saved} 件 保存しました")
        try:
            st.cache_data.clear()
        except Exception:
            pass

# =============================
# Header
# =============================
st.markdown(
    """
<div class="card cardGlow">
  <div style="display:flex; align-items:flex-end; justify-content:space-between; gap:12px;">
    <div>
      <div class="h1">⚡ Sales Intelligence</div>
      <div class="muted" style="margin-top:6px;">
        ALL（累積）/ MyFans / CandFans を同じUIで確認
      </div>
    </div>
    <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
      <span class="badge">dark × neon</span>
      <span class="badge">no-hover / no-zoom</span>
      <span class="badge">クリックで一覧表示</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# =============================
# Load data
# =============================
df_my_all = load_myfans_all(int(title_len))
df_ca_all = load_candfans_all(int(title_len))

dfs = [d for d in [df_my_all, df_ca_all] if isinstance(d, pd.DataFrame) and len(d) > 0]
if dfs:
    df_all = pd.concat(dfs, ignore_index=True)
else:
    df_all = pd.DataFrame(
        columns=["platform", "year_month", "occurred_at", "amount", "fee", "item_type", "title_raw", "title_short", "url"]
    )

df_all["occurred_at"] = pd.to_datetime(df_all["occurred_at"], errors="coerce")
df_all["amount"] = pd.to_numeric(df_all["amount"], errors="coerce").fillna(0)
df_all["fee"] = pd.to_numeric(df_all["fee"], errors="coerce").fillna(0)
df_all["year_month"] = df_all["year_month"].astype(str)

def admin_debug_panel(df_my_all=None, df_ca_all=None, df_all=None):
    """
    管理者向けデバッグ表示（Cloud差分の切り分け用）
    目的:
      - fonts/ の存在確認と Matplotlib フォント読み込み可否の確認
      - title_cache / uploads の存在確認
      - postランキングが空になる理由（title_short の有効件数）を可視化
    """
    try:
        if not is_admin:
            return
    except Exception:
        return

    import os
    import sys
    import platform as _platform
    from pathlib import Path as _Path

    with st.sidebar.expander("🛠 Debug（管理者専用・一時表示）", expanded=True):
        st.caption("Cloud差分の切り分け用。不要になったら admin_debug_panel 一塊を削除してください。")

        # -----------------------------
        # Runtime / Path
        # -----------------------------
        st.markdown("### Runtime / Path")
        try:
            st.write("python:", sys.version.split()[0])
            st.write("platform:", _platform.platform())
        except Exception as e:
            st.write("platform info error:", str(e))

        try:
            st.write("cwd:", os.getcwd())
        except Exception as e:
            st.write("cwd error:", str(e))

        try:
            base_dir = _Path(__file__).resolve().parent
            st.write("__file__ dir:", str(base_dir))
        except Exception as e:
            base_dir = None
            st.write("__file__ dir error:", str(e))

        # -----------------------------
        # Fonts
        # -----------------------------
        st.markdown("### Fonts")
        try:
            if base_dir is not None:
                fonts_dir = base_dir / "fonts"
            else:
                fonts_dir = _Path("fonts")
            st.write("fonts_dir:", str(fonts_dir), "exists=", fonts_dir.exists())

            if fonts_dir.exists():
                try:
                    st.write("fonts_dir list:", sorted([p.name for p in fonts_dir.iterdir() if p.is_file()]))
                except Exception as e:
                    st.write("fonts_dir list error:", str(e))

            # 期待ファイル候補（どれかあればOK）
            candidates = [
                fonts_dir / "app_font.ttf",
                fonts_dir / "app_font.otf",
                fonts_dir / "NotoSansJP-Regular.ttf",
                fonts_dir / "NotoSansJP-VariableFont_wght.ttf",
            ]
            existing = [p for p in candidates if p.exists()]
            st.write("font candidates found:", [p.name for p in existing])

            # Matplotlibでフォント名が取れるか（rcParamsは変更しない）
            try:
                from matplotlib import font_manager as _font_manager
                import matplotlib as _mpl

                font_name = None
                font_path_used = None
                if existing:
                    font_path_used = existing[0]
                    try:
                        # addfont は副作用（登録）あり。ただし rcParams は変更しない。
                        _font_manager.fontManager.addfont(str(font_path_used))
                        font_name = _font_manager.FontProperties(fname=str(font_path_used)).get_name()
                    except Exception as e:
                        st.write("addfont/get_name error:", str(e))

                st.write("font_path_used:", str(font_path_used) if font_path_used else "(none)")
                st.write("font_name:", font_name if font_name else "(none)")
                st.write("rcParams['font.family']:", _mpl.rcParams.get("font.family"))
                st.write("rcParams['font.sans-serif']:", _mpl.rcParams.get("font.sans-serif"))
            except Exception as e:
                st.write("matplotlib font debug error:", str(e))

        except Exception as e:
            st.write("fonts debug error:", str(e))

        # -----------------------------
        # Storage / cache
        # -----------------------------
        st.markdown("### Storage / Cache")
        try:
            # uploads dir (script内の Path("uploads") と一致するか確認)
            uploads_dir = (base_dir / "uploads") if base_dir is not None else _Path("uploads")
            st.write("uploads_dir:", str(uploads_dir), "exists=", uploads_dir.exists())
            if uploads_dir.exists():
                # 深すぎると重いので浅くだけ
                try:
                    st.write("uploads top entries:", sorted([p.name for p in uploads_dir.iterdir()])[:30])
                except Exception as e:
                    st.write("uploads list error:", str(e))
        except Exception as e:
            st.write("uploads debug error:", str(e))

        try:
            cache_path = (base_dir / "title_cache.sqlite3") if base_dir is not None else _Path("title_cache.sqlite3")
            st.write("title_cache.sqlite3 exists:", cache_path.exists(), "path:", str(cache_path))
        except Exception as e:
            st.write("title_cache debug error:", str(e))

        # -----------------------------
        # Data sanity (post ranking)
        # -----------------------------
        st.markdown("### Data sanity（投稿ランキングの空原因チェック）")

        def _post_title_stats(dfp, label):
            if dfp is None or not isinstance(dfp, pd.DataFrame) or dfp.empty:
                st.write(f"{label}: df is empty/None")
                return
            if "item_type" not in dfp.columns:
                st.write(f"{label}: no item_type column")
                return
            dpost = dfp[dfp["item_type"] == "post"].copy()
            st.write(f"{label}: post rows =", int(len(dpost)))
            if "title_short" not in dpost.columns:
                st.write(f"{label}: no title_short column")
                return
            s = dpost["title_short"].fillna("").astype(str)
            non_empty = int((s.str.len() > 0).sum())
            non_url = int((~s.str.startswith("http")).sum())
            valid = int(((s.str.len() > 0) & (~s.str.startswith("http"))).sum())
            st.write(f"{label}: title_short non-empty =", non_empty)
            st.write(f"{label}: title_short non-url =", non_url)
            st.write(f"{label}: title_short valid (non-empty & non-url) =", valid)

        _post_title_stats(df_my_all, "MyFans(all)")
        _post_title_stats(df_ca_all, "CandFans(all)")
        _post_title_stats(df_all, "ALL(all)")





# --- Admin Debug (TEMP) ---
admin_debug_panel(df_my_all=df_my_all, df_ca_all=df_ca_all, df_all=df_all)
# --- /Admin Debug (TEMP) ---

# =============================
# 年 / 月（年間）フィルタ（サイドバーではなくメイン上部に表示）
# ＋ 管理者のみ：MyFans タイトル一括取得（全期間）
# =============================

# --- compact controls (slider間隔を詰める) ---
st.markdown(
    """
<style>
/* スライダー/数値入力の縦の詰め（効きすぎると見づらいので控えめ） */
div[data-testid="stSlider"], div[data-testid="stNumberInput"]{
  margin-bottom: -6px !important;
}
div[data-testid="stSlider"] label, div[data-testid="stNumberInput"] label{
  margin-bottom: 2px !important;
}
</style>
""",
    unsafe_allow_html=True,
)

def available_years_months(df: pd.DataFrame):
    yms = sorted(
        [
            m
            for m in df["year_month"].dropna().unique().tolist()
            if re.match(r"^20\d{2}-\d{2}$", str(m))
        ]
    )
    years = sorted({ym.split("-")[0] for ym in yms})
    months_by_year = {}
    for y in years:
        months_by_year[y] = sorted({ym.split("-")[1] for ym in yms if ym.startswith(f"{y}-")})
    return years, months_by_year, yms



def filter_by_year_month(df: pd.DataFrame, selected_year: str, selected_month: str) -> pd.DataFrame:
    """df を選択中の年/月（または年間）に絞り込む。

    - df に year_month（YYYY-MM）があればそれを最優先
    - 次に occurred_at（datetime）から year/month を導出
    - それも無ければ date 文字列から推定（最後の手段）

    ※ UI 側の selected_month は '01' のような文字列、または '年間' を想定。
    """
    if df is None or df.empty:
        return df

    # selected_year は '2026' のような文字列を想定
    try:
        y = int(str(selected_year))
    except Exception:
        return df

    sm = str(selected_month)

    # 1) year_month があれば最優先（YYYY-MM）
    if "year_month" in df.columns:
        ym = df["year_month"].astype(str)
        if sm == "年間":
            return df[ym.str.startswith(f"{y}-")].copy()
        try:
            m = int(sm)
        except Exception:
            return df
        return df[ym == f"{y}-{m:02d}"].copy()

    # 2) occurred_at があれば year/month を導出
    if "occurred_at" in df.columns:
        occurred = pd.to_datetime(df["occurred_at"], errors="coerce")
        if sm == "年間":
            return df[occurred.dt.year == y].copy()
        try:
            m = int(sm)
        except Exception:
            return df
        return df[(occurred.dt.year == y) & (occurred.dt.month == m)].copy()

    # 3) date があれば文字列・datetime 両対応で絞り込む（最後の手段）
    if "date" in df.columns:
        d = pd.to_datetime(df["date"], errors="coerce")
        if sm == "年間":
            return df[d.dt.year == y].copy()
        try:
            m = int(sm)
        except Exception:
            return df
        return df[(d.dt.year == y) & (d.dt.month == m)].copy()

    return df


def admin_bulk_fetch_myfans_titles_all_period(df_all: pd.DataFrame):
    """
    MyFans（post）のURLからタイトルを「全期間」でまとめて取得する。
    - 各月で取得する件数（0=全URL）
    - 全体の上限（0=制限なし）
    """
    st.markdown("### 🔎 MyFans タイトル一括取得（全期間）")
    st.caption("※管理者モードのみ表示 / 年月フィルタとは独立（全期間対象）")

    if df_all is None or len(df_all) == 0:
        st.info("データがありません")
        return
    if "url" not in df_all.columns:
        st.error("url列がありません（CSV取り込みで url を作れていない可能性）")
        st.write("現在の列:", list(df_all.columns))
        return
    if "year_month" not in df_all.columns:
        st.error("year_month列がありません（CSV取り込みで year_month を作れていない可能性）")
        st.write("現在の列:", list(df_all.columns))
        return

    d = df_all[(df_all["platform"] == "myfans") & (df_all["item_type"] == "post")].copy()
    d["url"] = d["url"].astype(str)
    d = d[d["url"].str.startswith("http")]

    if len(d) == 0:
        st.info("MyFansの投稿URLがありません")
        return

    # UI（画像のやつを“ここ”にまとめて表示）
    cL, cR = st.columns([1, 1], gap="large")

    with cL:
        per_month = st.number_input("各月で取得する件数（0=全URL）", min_value=0, max_value=200, value=10, step=1, key="bulk_per_month")
        total_limit = st.number_input("全体の上限（0=制限なし）", min_value=0, max_value=20000, value=0, step=10, key="bulk_total_limit")

    with cR:
        timeout = st.slider("タイムアウト(秒)", 5, 30, 12, 1, key="bulk_timeout")
        min_sleep = st.slider("最小間隔(秒)", 1, 20, 4, 1, key="bulk_min_sleep")
        max_sleep = st.slider("最大間隔(秒)", 1, 30, 8, 1, key="bulk_max_sleep")
        max_retries = st.slider("リトライ回数", 0, 5, 2, 1, key="bulk_max_retries")

    b1, b2 = st.columns(2)
    with b1:
        do_fetch = st.button("✅ タイトル取得を実行", key="bulk_do_fetch")
    with b2:
        if st.button("🧹 キャッシュクリア（表示更新用）", key="bulk_clear_cache"):
            try:
                st.cache_data.clear()
            except Exception:
                pass
            st.success("キャッシュをクリアしました。必要ならページ再読み込み（Ctrl+F5）。")

    if not do_fetch:
        return

    # 取得対象URLを作る
    # per_month==0: 全URL（売上順）
    # per_month>0: 月ごとに上位N URL → 全体で合算して売上順
    if per_month == 0:
        url_rev = d.groupby("url", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        targets = url_rev["url"].tolist()
    else:
        targets_rows = []
        for ym, g in d.groupby("year_month"):
            url_rev_m = g.groupby("url", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            targets_rows.append(url_rev_m.head(int(per_month)))
        url_rev = pd.concat(targets_rows, ignore_index=True) if targets_rows else pd.DataFrame(columns=["url", "amount"])
        url_rev = url_rev.groupby("url", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        targets = url_rev["url"].tolist()

    if total_limit and total_limit > 0:
        targets = targets[: int(total_limit)]

    # 既存キャッシュを除外
    to_fetch = [u for u in targets if not get_cached_title(u)]
    st.write(f"対象URL: {len(targets):,} / 未取得: {len(to_fetch):,}")

    if not to_fetch:
        st.info("未取得URLがありません（すでにキャッシュ済み）")
        return

    st.markdown("#### 実行ログ")
    log_area = st.empty()
    prog = st.progress(0)

    ok, fail = 0, 0
    fail_rows = []

    for i, u in enumerate(to_fetch):
        try:
            t = fetch_title_from_web(u, timeout=int(timeout), max_retries=int(max_retries))
            set_cached_title(u, t or "")
            if t:
                ok += 1
                log_area.write(f"✅ OK: {u} → {t[:80]}")
            else:
                fail += 1
                log_area.write(f"⚠️ EMPTY: {u}")
        except Exception as e:
            set_cached_title(u, "")
            fail += 1
            msg = str(e)
            fail_rows.append({"url": u, "error": msg})
            log_area.write(f"❌ FAIL: {u} → {msg}")

        time.sleep(random.uniform(float(min_sleep), float(max_sleep)))
        prog.progress((i + 1) / len(to_fetch))

    st.success(f"完了: success={ok}, failed={fail}")

    if fail_rows:
        st.markdown("#### 失敗一覧")
        st.dataframe(pd.DataFrame(fail_rows), use_container_width=True)

    # 反映
    try:
        st.cache_data.clear()
    except Exception:
        pass
    st.info("反映のため、必要ならページを再読み込みしてください（Ctrl+F5）。")


years, months_by_year, all_yms = available_years_months(df_all)

# UI：右側に 年/月、左側に（管理者のみ）タイトル一括取得
hdr_l, hdr_r = st.columns([3, 2])

with hdr_l:
    if is_admin:
        with st.expander("🔎 MyFans タイトル一括取得（全期間）", expanded=False):
            admin_bulk_fetch_myfans_titles_all_period(df_all)
    else:
        st.markdown("")

with hdr_r:
    if years:
        sel_year = st.selectbox("年", years, index=len(years) - 1, key="sel_year")
        month_opts = ["年間"] + months_by_year.get(sel_year, [])
        sel_month = st.selectbox("月", month_opts, index=0, key="sel_month")
    else:
        sel_year = None
        sel_month = None
        st.info("年月データがありません")

# ---- normalize selector vars (keep compatibility) ----
selected_year = sel_year
selected_month = sel_month
selected_month_num = None
if selected_month not in (None, "年間"):
    try:
        selected_month_num = int(selected_month)
    except Exception:
        selected_month_num = None
# ------------------------------------------------------


# =============================
# Helper: show dataframe (admin shows url)
# =============================
def show_df(df: pd.DataFrame, max_rows=200):
    d = df.copy().sort_values("occurred_at", ascending=False)
    if not is_admin:
        d = d.drop(columns=["url", "title_raw"], errors="ignore")
    st.dataframe(d.head(max_rows), use_container_width=True)

# =============================
# Matplotlib: 固定（画像化して表示）
# =============================

# =============================
# Admin Debug Panel (TEMP)
# - 管理者(is_admin)だけに常時表示
# - 既存ロジックから独立（ここ一塊を削除すれば完全に消える）
# =============================
def mpl_setup():
    matplotlib.rcParams["font.family"] = ["Meiryo", "Yu Gothic", "Noto Sans JP", "sans-serif"]
    matplotlib.rcParams["axes.unicode_minus"] = False

def fig_to_image(fig):
    buf = BytesIO()
    # 画質アップ（鮮明化）
    fig.savefig(
        buf,
        format="png",
        dpi=320,
        bbox_inches="tight",
        pad_inches=0.08,
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)
    buf.seek(0)
    return buf

def chart_daily_line_img(df, title, color_hex, height_px=380, overlays=None, x_mode="daily"):
    """
    df: columns: occurred_at, amount, (optional) platform, item_type
    color_hex: str or (str,str) for gradient
    overlays:
      - (platform, color, linestyle)
      - (platform, color, linestyle, "plan" or "post")
    x_mode: "daily" or "monthly"
    """
    if df is None or len(df) == 0:
        return None

    d = df.copy()

    # ---- date column build (daily/monthly) ----
    if "occurred_at" in d.columns:
        d = d.dropna(subset=["occurred_at"])
        if len(d) == 0:
            return None
        dt = pd.to_datetime(d["occurred_at"], errors="coerce")
    elif "date" in d.columns:
        dt = pd.to_datetime(d["date"], errors="coerce")
    else:
        return None

    if x_mode == "monthly":
        # 月次：各月の1日を代表日にする（折れ線向き）
        d["date"] = dt.dt.to_period("M").dt.to_timestamp()
        # monthly なのに1ヶ月分しか無いと線が潰れるので日別へ自動フォールバック（A案）
        if d["date"].dt.to_period("M").nunique() <= 1:
            x_mode = "daily"
            d["date"] = dt.dt.floor("D")
            if "※1ヶ月分のため日別表示" not in title:
                title = f"{title} ※1ヶ月分のため日別表示"
    else:
        d["date"] = dt.dt.floor("D")

    d["amount"] = pd.to_numeric(d.get("amount", 0), errors="coerce").fillna(0)

    # ---- aggregate main series ----
    g = d.groupby("date", as_index=False)["amount"].sum().sort_values("date")
    if len(g) == 0:
        return None

    x = g["date"].tolist()
    y = g["amount"].astype(float).tolist()

    # =========================
    # Size / Fonts（折れ線のみ）
    # =========================
    tick_fs = 15          # 軸の値（目盛り）: 1.5倍相当
    axis_label_fs = 20    # 軸ラベル: 3倍相当

    fig_w = 12
    fig_h = max(2.2, height_px / 120.0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=220)

    # ---- background ----
    fig.patch.set_alpha(0.0)
    ax.set_facecolor((0, 0, 0, 0))

    # ---- grid / ticks ----
    ax.grid(True, alpha=0.15)
    ax.tick_params(axis="x", colors="#CFCFD6", labelsize=tick_fs, pad=2)
    ax.tick_params(axis="y", colors="#CFCFD6", labelsize=tick_fs, pad=2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: fmt_yen(x)))

    ax.spines["bottom"].set_color("#444455")
    ax.spines["left"].set_color("#444455")
    ax.spines["top"].set_color("#00000000")
    ax.spines["right"].set_color("#00000000")

    # ---- legend labels / handles ----
    legend_handles = []
    title_str = str(title)
    if title_str.startswith("ALL"):
        main_label = "ALL"
    else:
        main_label = "合計"

    # ---- main line ----
    if isinstance(color_hex, (tuple, list)) and len(color_hex) >= 2:
        c1, c2 = color_hex[0], color_hex[1]
        from matplotlib.collections import LineCollection

        pts = np.array([mdates.date2num(x), y]).T.reshape(-1, 1, 2)
        segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
        lc = LineCollection(segs, linewidths=2.6, capstyle="round")
        colors = _multi_stop_grad_colors([c1, c2], len(segs))
        lc.set_colors(colors)
        ax.add_collection(lc)

        # legend proxy (LineCollection は凡例に出ないため)
        from matplotlib.lines import Line2D
        legend_handles.append(Line2D([0], [0], color=c2, linewidth=2.8, label=main_label))

        ax.set_xlim(mdates.date2num(x[0]), mdates.date2num(x[-1]))
        ax.set_ylim(min(y) * 0.95 if min(y) >= 0 else min(y) * 1.05, max(y) * 1.05)
    else:
        line_main, = ax.plot(x, y, color=color_hex, linewidth=2.8, solid_capstyle="round", label=main_label)
        legend_handles.append(line_main)

    # ---- overlays (dashed / dotted) ----
    if overlays:
        try:
            all_dates = pd.to_datetime(g["date"])
            for item in overlays:
                # item: (plat, col, ls) or (plat, col, ls, kind)
                if len(item) == 3:
                    plat, col, ls = item
                    kind = None
                else:
                    plat, col, ls, kind = item[0], item[1], item[2], item[3]

                dd = d.copy()
                if "platform" in dd.columns:
                    dd = dd[dd["platform"] == plat]

                if kind in ("plan", "post") and "item_type" in dd.columns:
                    dd = dd[dd["item_type"] == kind]

                if len(dd) == 0:
                    continue

                gg = dd.groupby("date", as_index=True)["amount"].sum()
                gg = gg.reindex(all_dates, fill_value=0.0)

                # 凡例ラベル（hover無しの画像でも判別できるように）
                if kind == "plan":
                    ov_label = "プラン"
                elif kind == "post":
                    ov_label = "投稿"
                else:
                    if str(plat) == "myfans":
                        ov_label = "MyFans"
                    elif str(plat) == "candfans":
                        ov_label = "CandFans"
                    else:
                        ov_label = str(plat)

                line_ov, = ax.plot(
                    all_dates.tolist(),
                    gg.astype(float).tolist(),
                    color=col,
                    linestyle=ls,
                    linewidth=2.2,
                    alpha=0.95,
                    label=ov_label,
                    solid_capstyle="round",
                )
                legend_handles.append(line_ov)
        except Exception:
            pass

    # ---- legend (x軸の下に横並び) ----
    if legend_handles:
        leg = ax.legend(
            handles=legend_handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.24),
            ncol=min(3, len(legend_handles)),
            frameon=False,
            fontsize=13,
        )
        for t in leg.get_texts():
            t.set_color("#CFCFD6")

    # ---- titles / labels ----
    ax.set_title(title, color="#EAF0FF", fontsize=14, pad=8, fontweight="bold")
    ax.set_xlabel("日付", color="#CFCFD6", fontsize=axis_label_fs, labelpad=8)
    ax.set_ylabel("売上（円）", color="#CFCFD6", fontsize=axis_label_fs, labelpad=10)

    # X-axis format
    if x_mode == "monthly":
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    for lbl in ax.get_xticklabels():
        lbl.set_rotation(0)

    # ---- margins (余白減) ----
    ax.margins(x=0.01, y=0.08)
    fig.tight_layout(pad=0.15)

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=220,
        transparent=True,
        bbox_inches="tight",
        pad_inches=0.02,
    )
    plt.close(fig)
    buf.seek(0)
    return buf




def _hex_to_rgb01(h: str):
    h = (h or "").lstrip("#")
    if len(h) != 6:
        return (1.0, 1.0, 1.0)
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b)

def _rgb01_to_hex(rgb):
    r = int(max(0, min(1, rgb[0])) * 255)
    g = int(max(0, min(1, rgb[1])) * 255)
    b = int(max(0, min(1, rgb[2])) * 255)
    return f"#{r:02X}{g:02X}{b:02X}"

def _lerp(a, b, t: float):
    return a + (b - a) * t

def _grad_colors(base_hex: str, n: int, end_hex: str = "#FFE6E6", speed: float = 1.8):
    """
    base -> end のグラデーション色を n 個作る
    speed を上げるほど、序盤から早く薄くなる（= 2番目が従来の3番目くらいの薄さになる）
    """
    if n <= 1:
        return [base_hex]

    base = _hex_to_rgb01(base_hex)
    end = _hex_to_rgb01(end_hex)

    cols = []
    for i in range(n):
        t = i / (n - 1)
        t = min(1.0, t * speed)  # ★ここが「2番目を薄くする」ポイント
        rgb = (_lerp(base[0], end[0], t), _lerp(base[1], end[1], t), _lerp(base[2], end[2], t))
        cols.append(_rgb01_to_hex(rgb))
    return cols

def _multi_stop_grad_colors(stops_hex: list, n: int):
    """
    stops_hex: ["#AE33F5", "#5C4BFA", "#0066FF"] のような多段の色ストップ
    n: 必要な色数

    重要:
    - n が stops の数以下なら「上から順」に stops をそのまま使う（補間しない）
      → 円グラフ3要素なら 3色がそのまま反映される
    - n が stops より多い場合だけ、区間補間で増やす
    """
    if n <= 0:
        return []
    if not stops_hex:
        return ["#FFFFFF"] * n
    if len(stops_hex) == 1:
        return [stops_hex[0]] * n

    # ★ここが今回のキモ：小さいnなら補間せず、そのまま使う
    if n <= len(stops_hex):
        return [stops_hex[i] for i in range(n)]

    # ここから下は「増やす必要がある」時だけ補間
    if n == 1:
        return [stops_hex[0]]

    segs = len(stops_hex) - 1

    def h2rgb(h):
        h = str(h).lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def rgb2h(rgb):
        return "#{:02X}{:02X}{:02X}".format(*rgb)

    rgbs = [h2rgb(h) for h in stops_hex]

    out = []
    for k in range(n):
        t = k / (n - 1)  # 0..1
        pos = t * segs
        i = int(pos)
        if i >= segs:
            i = segs - 1
            local = 1.0
        else:
            local = pos - i

        r1, g1, b1 = rgbs[i]
        r2, g2, b2 = rgbs[i + 1]
        r = int(r1 + (r2 - r1) * local)
        g = int(g1 + (g2 - g1) * local)
        b = int(b1 + (b2 - b1) * local)
        out.append(rgb2h((r, g, b)))

    return out

def plan_pie_img(df: pd.DataFrame, title: str, height_px: int):
    """固定画像の円グラフ（hover無し）
    - ALL のとき：MyFans+CandFans を統合して 3カテゴリ（顔出し最強プラン/バックナンバー/こた倶楽部）で表示
    - MyFans/CandFans のとき：そのままプラン別に表示
    仕様：多い順に並べて、時計回り（counterclock=False）
    """
    if df is None or len(df) == 0:
        st.info("planデータがありません")
        return

    d = df[df["item_type"] == "plan"].copy()
    if len(d) == 0:
        st.info("planデータがありません")
        return

    # URLっぽいものは除外
    d = d[~d["title_short"].fillna("").astype(str).str.startswith("http")]
    if len(d) == 0:
        st.info("planデータがありません")
        return

    mpl_setup()

    is_all = title.startswith("ALL")

    def _canon_plan_name(s: str) -> str:
        s = str(s)
        s = s.replace(" ", "").replace("　", "")

        if "顔出し最強" in s or "最強" in s:
            return "顔出し最強プラン"

        # ★ ここが今回の追加ポイント
        if (
            ("バックナンバー" in s or "バックナンバ" in s)
            and ("単月" in s or "1ヶ月" in s or "１ヶ月" in s)
        ):
            return "バックナンバー(単月)"

        if "バックナンバー" in s or "バックナンバ" in s:
            return "バックナンバー"

        if "こた倶楽部" in s or "こたクラブ" in s:
            return "こた倶楽部"

        return "その他"


    if is_all:
        # 統合して3カテゴリ（＋その他があれば最後に）
        d["canon"] = d["title_short"].apply(_canon_plan_name)
        # ALLでは「バックナンバー(単月)」もバックナンバーに統合して3カテゴリに寄せる
        d["canon"] = d["canon"].replace({"バックナンバー(単月)": "バックナンバー"})
        g = (
            d.groupby("canon", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
        )

        labels = g["canon"].astype(str).tolist()
        values = g["amount"].astype(float).tolist()

        # ALLの円グラフ色（配色C）。COLORSにALL_PIEがあればそれを優先
        default_all_pie = ["#FF3B3B", "#4EF282", "#2E7BFF"]  # ネオン三原色（赤/緑/青）
        if "ALL_PIE" in COLORS and isinstance(COLORS["ALL_PIE"], (list, tuple)) and len(COLORS["ALL_PIE"]) >= 3:
            base_cols = list(COLORS["ALL_PIE"])
        else:
            base_cols = default_all_pie

        colors = _multi_stop_grad_colors(base_cols[:3], len(values))

    else:
        # MyFans / CandFans：プラン名を正式名称へ正規化して集計（色固定のため）
        d["canon"] = d["title_short"].apply(_canon_plan_name)
        g = (
            d.groupby(["canon"], as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
        )
        labels = g["canon"].astype(str).tolist()
        values = g["amount"].astype(float).tolist()

        # platform から My/Cand を判断
        plat = "myfans"
        if "platform" in d.columns and len(d["platform"].dropna()) > 0:
            plat = str(d["platform"].dropna().iloc[0])

        plan_color_map = COLORS.get("MY_PLAN_COLORS", {}) if plat == "myfans" else COLORS.get("CA_PLAN_COLORS", {})
        fallback_stops = COLORS["MY_PIE"] if plat == "myfans" else COLORS["CA_PIE"]
        fallback_cols = _multi_stop_grad_colors(fallback_stops, len(labels))

        colors = []
        for i, lab in enumerate(labels):
            c = plan_color_map.get(lab)
            colors.append(c if c else fallback_cols[i])

    total = float(sum(values)) if values else 0.0
    if total <= 0:
        st.info("plan金額がありません")
        return

    # サイズ：棒グラフと同程度にしたい → height_px を反映
    pie_scale = 1.5  # ★ 円グラフ直径スケール（1.5倍）
    pie_radius = 1.0 * pie_scale

    fig_w = 11 * pie_scale
    fig_h = max(3.2, height_px / 90.0) * pie_scale
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=(0, 0, 0, 0), dpi=220)
    ax = fig.add_subplot(111)
    ax.set_facecolor((1, 1, 1, 0.03))

    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,  # ★ 時計回り
        radius=pie_radius,
        wedgeprops={"edgecolor": COLORS.get("PIE_EDGE", "#696969"), "linewidth": 1.0},
    )

    ax.set_title(title, color="#EAF0FF", fontsize=48, pad=14, fontweight="bold")

    # 吹き出し（プラン名の下に金額・割合）
    used_tys = {"L": [], "R": []}
    for i, w in enumerate(wedges):
        ang = (w.theta2 + w.theta1) / 2.0
        x = np.cos(np.deg2rad(ang))
        y = np.sin(np.deg2rad(ang))

        pct = (float(values[i]) / total) * 100.0
        txt = f"{labels[i]}\n{fmt_yen(values[i])}  ({fmt_pct(pct)})"

        side = "R" if x >= 0 else "L"

        # 小さい比率は外側へ（衝突しやすいので）
        base_tx = 1.60
        base_ty = 1.25
        if pct < 3.0:
            base_tx = 1.85
            base_ty = 1.35

        tx = base_tx * pie_scale * np.sign(x)
        ty = base_ty * pie_scale * y

        # ざっくり衝突回避：同じ側で近すぎるtyを少しずらす
        bump = 0.12 * pie_scale
        tries = 0
        while any(abs(ty - u) < bump for u in used_tys[side]) and tries < 20:
            ty += bump if ty >= 0 else -bump
            tries += 1
        used_tys[side].append(ty)

        ax.annotate(
            txt,
            xy=(x * pie_radius * 1.06, y * pie_radius * 1.06),
            xytext=(tx, ty),
            textcoords="data",
            ha="left" if x >= 0 else "right",
            va="center",
            fontsize=24.0,
            fontweight="bold",
            linespacing=1.15,
            color="#EAF0FF",
            bbox=dict(boxstyle="round,pad=0.35", fc=(0, 0, 0, 0.35), ec=(1, 1, 1, 0.18), lw=0.8),
            arrowprops=dict(
                arrowstyle="-|>",
                color=(1, 1, 1, 0.30),
                lw=0.8,
                shrinkA=0,
                shrinkB=0,
                connectionstyle="arc3,rad=0.2",
            ),
        )

    ax.axis("equal")
    fig.tight_layout()
    st.image(fig_to_image(fig), use_container_width=True)


def top_bars_img(
    df: pd.DataFrame,
    item_type: str,
    title: str,
    topn: int = 10,
    color_spec=None,   # "#RRGGBB" or {"myfans":"#..", "candfans":"#.."}
    color_hex: str = None,  # 互換用（古い呼び出し対策）
    height_px: int = 320,
) -> pd.DataFrame:
    """
    画像として棒グラフを描画（hover/ズーム/パンが一切出ない）
    返り値は集計済みDataFrame（title_shortごとのamount合計）
    """
    d = df[df["item_type"] == item_type].copy()

    # URLのまま / title_short空 はランキングに出さない
    d = d[d["title_short"].astype(str).str.len() > 0]
    d = d[~d["title_short"].astype(str).str.startswith("http")]

    if len(d) == 0:
        st.info("データがありません")
        return pd.DataFrame()

    g_cols = ["title_short"]
    if "platform" in d.columns:
        g_cols = ["platform", "title_short"]

    g = (
        d.groupby(g_cols, as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(int(topn))
    )

    # 表示用に反転（上が1位）
    g = g.iloc[::-1].reset_index(drop=True)

    mpl_setup()

    n = len(g)
    base_h = 2.8 if height_px <= 320 else 3.8
    fig_h = max(base_h, 0.45 * n + 1.2)

    fig = plt.figure(figsize=(11, fig_h), facecolor=(0, 0, 0, 0))
    ax = fig.add_subplot(111)
    ax.set_facecolor((1, 1, 1, 0.03))

    vals = g["amount"].astype(float).values
    labels = g["title_short"].astype(str).tolist()
    y = np.arange(n)

    # 色決定（ALLのとき platform ごとに色を変える）
    if color_spec is None and color_hex is not None:
        color_spec = color_hex
    if color_spec is None:
        color_spec = "#3CF6FF"

    if isinstance(color_spec, dict) and "platform" in g.columns:
        base_cols = [color_spec.get(p, "#999999") for p in g["platform"].tolist()]
    else:
        base_cols = [str(color_spec)] * n

    # ネオン感：少し明暗を揺らす
    def _shade(hex_color: str, k: float):
        hex_color = str(hex_color).lstrip("#")
        if len(hex_color) != 6:
            return (0.7, 0.7, 0.7, 0.95)
        r = int(hex_color[0:2], 16) / 255.0
        g_ = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        r = min(1.0, max(0.0, r * k))
        g_ = min(1.0, max(0.0, g_ * k))
        b = min(1.0, max(0.0, b * k))
        return (r, g_, b, 0.95)

    shades = []
    for i in range(n):
        k = 0.92 + (i % 3) * 0.06
        shades.append(_shade(base_cols[i], k))

    bars = ax.barh(y, vals, color=shades, edgecolor=(1, 1, 1, 0.14), linewidth=1.0)

    # 値ラベル（右端に¥）
    vmax = float(max(vals)) if len(vals) else 0.0
    for b, v in zip(bars, vals):
        ax.text(
            b.get_width() + (vmax * 0.02 if vmax > 0 else 1),
            b.get_y() + b.get_height() / 2,
            fmt_yen(v),
            va="center",
            ha="left",
            color="#EAF0FF",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, color="#EAF0FF", fontsize=10, fontweight="bold")

    ax.set_xlabel("売上（円）", color="#EAF0FF", fontsize=10, labelpad=8)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: fmt_yen(x)))
    ax.set_title(title, color="#EAF0FF", fontsize=13, pad=12, fontweight="bold")

    ax.tick_params(axis="x", colors="#EAF0FF", labelsize=9)
    ax.grid(True, axis="x", color=(1, 1, 1, 0.08), linewidth=0.8)
    ax.grid(False, axis="y")
    for spine in ax.spines.values():
        spine.set_color((1, 1, 1, 0.12))

    fig.tight_layout()
    st.image(fig_to_image(fig), use_container_width=True)
    return g

def kpis(df: pd.DataFrame):
    total = int(df["amount"].sum())
    plan = int(df[df["item_type"] == "plan"]["amount"].sum())
    post = int(df[df["item_type"] == "post"]["amount"].sum())
    cnt = int(len(df))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("総売上", fmt_yen(total))
    c2.metric("プラン売上", fmt_yen(plan))
    c3.metric("投稿売上", fmt_yen(post))
    c4.metric("件数", f"{cnt:,}")

# =============================
# Admin: MyFans fetch titles (TOP-N by revenue)
# =============================
def admin_fetch_myfans_titles(df_my: pd.DataFrame):
    st.markdown("### 🔧 MyFans 投稿URL → タイトル取得（上位のみ）")
    st.caption("取得後は自動反映します（キャッシュクリアもボタンで可能）。")

    if "url" not in df_my.columns:
        st.error("df_my に url 列がありません（CSV取り込みで url を作れていない可能性）")
        st.write("現在の列:", list(df_my.columns))
        return

    d = df_my[df_my["item_type"] == "post"].copy()
    d["url"] = d["url"].astype(str)
    d = d[d["url"].str.startswith("http")]

    if len(d) == 0:
        st.error("投稿URLが0件です。MyFans CSV の『対象URL』列が空/列名違いの可能性があります。")
        return

    url_rev = d.groupby("url", as_index=False)["amount"].sum().sort_values("amount", ascending=False)

    st.markdown("#### 対象URL（売上上位）")
    st.dataframe(url_rev.head(30), use_container_width=True)

    topn = st.number_input("取得するTOP N", 1, 50, 10, 1)
    timeout = st.slider("タイムアウト(秒)", 5, 30, 12, 1)
    min_sleep = st.slider("最小間隔(秒)", 1, 20, 4, 1)
    max_sleep = st.slider("最大間隔(秒)", 1, 30, 8, 1)
    max_retries = st.slider("リトライ回数", 0, 5, 2, 1)

    colA, colB = st.columns(2)
    with colA:
        do_fetch = st.button("✅ TOP N のタイトル取得を実行")
    with colB:
        if st.button("🧹 キャッシュクリア（表示更新用）"):
            try:
                st.cache_data.clear()
            except Exception:
                pass
            st.success("キャッシュをクリアしました。必要ならページ再読み込み（Ctrl+F5）。")

    if not do_fetch:
        return

    targets = url_rev.head(int(topn))["url"].tolist()
    to_fetch = [u for u in targets if not get_cached_title(u)]
    if not to_fetch:
        st.info("未取得URLがありません（すでにキャッシュ済み）")
        return

    st.markdown("#### 実行ログ")
    log_area = st.empty()

    prog = st.progress(0)
    ok, fail = 0, 0
    fail_rows = []

    for i, u in enumerate(to_fetch):
        try:
            t = fetch_title_from_web(u, timeout=int(timeout), max_retries=int(max_retries))
            set_cached_title(u, t or "")
            ok += 1 if t else 0
            fail += 0 if t else 1
            log_area.write(f"✅ OK: {u} → {t[:80] if t else '(empty)'}")
        except Exception as e:
            set_cached_title(u, "")
            fail += 1
            msg = str(e)
            fail_rows.append({"url": u, "error": msg})
            log_area.write(f"❌ FAIL: {u} → {msg}")

        time.sleep(random.uniform(float(min_sleep), float(max_sleep)))
        prog.progress((i + 1) / len(to_fetch))

    st.success(f"完了: success={ok}, failed={fail}")

    if fail_rows:
        st.markdown("#### 失敗一覧")
        st.dataframe(pd.DataFrame(fail_rows), use_container_width=True)

    try:
        st.cache_data.clear()
    except Exception:
        pass
    st.info("反映のため、必要ならページを再読み込みしてください（Ctrl+F5）。")

# =============================
# “全文タイトル表示” UI（クリック/タップ）
# 仕様：2行目（長文）を表示しない → タイトル（短）と合計金額のみ
# =============================
def full_title_panel(g: pd.DataFrame, title: str):
    """
    g: top_bars_img が返す集計結果（想定）
       必須: amount, title/title_short 等
       ALLの場合は platform 列があれば色付き■を付ける
    """
    with st.expander(f"📄 {title} タイトル一覧（クリック/タップで開く）", expanded=False):
        st.caption("※ホバーは一切出ません。ここでタイトルと合計金額のみ確認できます。")

        if g is None or len(g) == 0:
            st.info("投稿データがありません")
            return

        df = g.copy()

        # 列ゆれ吸収
        if "amount" not in df.columns and "sales" in df.columns:
            df = df.rename(columns={"sales": "amount"})
        if "title" not in df.columns and "title_short" in df.columns:
            df = df.rename(columns={"title_short": "title"})
        if "title" not in df.columns and "name" in df.columns:
            df = df.rename(columns={"name": "title"})

        if "title" not in df.columns or "amount" not in df.columns:
            st.write(df.head())
            return

        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        # 売上の高い順にランキング
        df = df.sort_values("amount", ascending=False).reset_index(drop=True)

        my_col = COLORS.get("MY_LINE", "#FF0000")   # MyFansの色（赤系）
        ca_col = COLORS.get("CA_LINE", "#380061")   # CandFansの色（紫系）

        for i, row in enumerate(df.itertuples(index=False), start=1):
            t = str(getattr(row, "title", "") or "")
            a = float(getattr(row, "amount", 0.0))

            # ALL の場合だけ platform に応じて色付き■を付ける（platform列があるとき）
            prefix = ""
            if "platform" in df.columns:
                plat = getattr(row, "platform", "")
                if plat == "myfans":
                    prefix = f'<span style="color:{my_col};font-weight:900;">■</span> '
                elif plat == "candfans":
                    prefix = f'<span style="color:{ca_col};font-weight:900;">■</span> '

            st.markdown(
                f'{prefix}<span style="font-weight:800;">{i}位：</span>'
                f'<span style="font-weight:700;">{t}</span> '
                f'<span style="color:#CFCFD6;">({fmt_yen(a)})</span>',
                unsafe_allow_html=True,
            )


#全文タイトルランキング表示

def render_post_ranking(g_post: pd.DataFrame, title_prefix: str):
    """
    g_post: top_bars_img に渡している元データの集計結果（想定）
           必須列：title, amount
           ALLの場合は platform 列があれば色■を出す
    """
    if g_post is None or len(g_post) == 0:
        st.info("投稿データがありません")
        return

    df = g_post.copy()

    # 想定列名の揺れに対応
    if "title" not in df.columns:
        if "name" in df.columns:
            df = df.rename(columns={"name": "title"})
    if "amount" not in df.columns:
        if "sales" in df.columns:
            df = df.rename(columns={"sales": "amount"})

    if "title" not in df.columns or "amount" not in df.columns:
        # どうしても形式が違う場合は既存にフォールバック
        full_title_panel(g_post, f"{title_prefix} 投稿TOP")
        return

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df.sort_values("amount", ascending=False)

    # 表示用（URLっぽいのは除外したい方針ならここで落とせる）
    # df = df[~df["title"].astype(str).str.startswith("http")]

    my_col = COLORS.get("MY_LINE", "#FF0000")
    ca_col = COLORS.get("CA_LINE", "#380061")

    # タイトル一覧
    st.markdown("### 🏆 投稿ランキング（売上）")
    for i, row in enumerate(df.itertuples(index=False), start=1):
        t = str(getattr(row, "title", ""))
        a = float(getattr(row, "amount", 0.0))

        # ALLなら platform 列があれば色■を付ける
        prefix = ""
        if title_prefix == "ALL" and "platform" in df.columns:
            plat = getattr(row, "platform", "")
            if plat == "myfans":
                prefix = f'<span style="color:{my_col};font-weight:800;">■</span> '
            elif plat == "candfans":
                prefix = f'<span style="color:{ca_col};font-weight:800;">■</span> '

        # 1行で見やすく（長いタイトルは折り返す）
        st.markdown(
            f'{i}位：{prefix}<span style="font-weight:700;">{t}</span> '
            f'<span style="color:#CFCFD6;">（{a:,.0f}円）</span>',
            unsafe_allow_html=True,
        )


# =============================
# Layout helpers
# =============================
def render_kpis_with_breakdown(df: pd.DataFrame, title_prefix: str):
    # 基本KPI（合計 / plan / post）
    def _sum_amount(sub: pd.DataFrame) -> float:
        if sub is None or len(sub) == 0:
            return 0.0
        return float(pd.to_numeric(sub["amount"], errors="coerce").fillna(0).sum())

    total_amt = _sum_amount(df)
    plan_amt  = _sum_amount(df[df.get("item_type") == "plan"]) if "item_type" in df.columns else 0.0
    post_amt  = _sum_amount(df[df.get("item_type") == "post"]) if "item_type" in df.columns else 0.0

    # 表示（3カラム）
    c1, c2, c3 = st.columns(3, gap="large")

    def _breakdown_lines(sub_df: pd.DataFrame, base_total: float):
        # My/Cand の内訳（金額＋割合）
        if "platform" not in sub_df.columns:
            return []
        my = _sum_amount(sub_df[sub_df["platform"] == "myfans"])
        ca = _sum_amount(sub_df[sub_df["platform"] == "candfans"])
        denom = base_total if base_total > 0 else (my + ca if (my + ca) > 0 else 1.0)

        my_pct = my / denom * 100.0
        ca_pct = ca / denom * 100.0

        my_col = COLORS.get("MY_LINE", "#FF0000")
        ca_col = COLORS.get("CA_LINE", "#380061")

        return [
            f'<span style="color:{my_col};font-weight:700;font-size:12px;">■</span> '
            f'<span style="font-size:12px;">MyFans　{my:,.0f}円（{my_pct:.1f}%）</span>',
            f'<span style="color:{ca_col};font-weight:700;font-size:12px;">■</span> '
            f'<span style="font-size:12px;">CandFans　{ca:,.0f}円（{ca_pct:.1f}%）</span>',
        ]


    with c1:
        st.metric("総売上", f"{total_amt:,.0f}円")
        if title_prefix == "ALL":
            lines = _breakdown_lines(df, total_amt)
            if lines:
                st.markdown("<br>".join(lines), unsafe_allow_html=True)

    with c2:
        st.metric("プラン売上", f"{plan_amt:,.0f}円")
        if title_prefix == "ALL" and "item_type" in df.columns:
            d_plan = df[df["item_type"] == "plan"]
            lines = _breakdown_lines(d_plan, plan_amt)
            if lines:
                st.markdown("<br>".join(lines), unsafe_allow_html=True)

    with c3:
        st.metric("投稿売上", f"{post_amt:,.0f}円")
        if title_prefix == "ALL" and "item_type" in df.columns:
            d_post = df[df["item_type"] == "post"]
            lines = _breakdown_lines(d_post, post_amt)
            if lines:
                st.markdown("<br>".join(lines), unsafe_allow_html=True)

    st.markdown("")  # 余白


def section_overview(df: pd.DataFrame, line_color, title_prefix: str):
    if df is None or len(df) == 0:
        st.warning("データがありません。管理者モードでアップロードしてください。")
        return

    render_kpis_with_breakdown(df, title_prefix)

    line_h = 800 if mobile_mode else 800
    bar_h = 500 if mobile_mode else 550  # 円も棒並みに

    # 年間なら月別、それ以外は日別
    x_mode = "monthly" if (selected_month == "年間") else "daily"

        # ym label (year/month)
    # selected_year / selected_month を必ず使い、selected には依存しない
    try:
        if str(selected_month) == "年間":
            ym_label = f"{selected_year}年(年間)"
        else:
            ym_label = f"{selected_year}年{int(selected_month):02d}月"
    except Exception:
        ym_label = f"{selected_year}-{selected_month}"


    # 線種（★分岐の外で必ず定義★）
    DASH = (0, (6, 4))   # 破線
    DOT  = (0, (1, 2))   # さらに細かい破線（点線っぽい）


    # 折れ線用の描画データ（ALLのみ例外で差し替える）
    df_line = df
    # 色ルール：
    # - ALL: ALLは見やすい黄色（後で調整OK）、My/Candは各個別と同じ色（破線）
    # - My/Cand: 3本を円グラフ色に合わせる（合計=1色目、plan=2色目、post=3色目）
        # ---- line chart colors / overlays ----
    if title_prefix == "ALL":
        # ALLの折れ線表示ルール：
        # - MyFans or CandFans の片方しか無い場合：無い方＆ALL合計は出さず、存在する方のみ表示
        # - 両方ある場合：ALL(実線) + MyFans/CandFans(破線)
        df_line = df
        plats = set()
        if "platform" in df.columns:
            plats = set([str(x) for x in df["platform"].dropna().unique().tolist()])

        if plats == {"myfans"}:
            df_line = df[df["platform"] == "myfans"].copy()
            main_color = COLORS["MY_LINE"]
            overlays = []
        elif plats == {"candfans"}:
            df_line = df[df["platform"] == "candfans"].copy()
            main_color = COLORS["CA_LINE"]
            overlays = []
        else:
            main_color = COLORS["ALL_LINE"]
            overlays = [
                ("myfans", COLORS["MY_LINE"], DASH, None),     # MyFans total（破線）
                ("candfans", COLORS["CA_LINE"], DASH, None),   # CandFans total（破線）
            ]
    elif title_prefix == "MyFans":
        main_color = COLORS["MY_LINE"]  # total
        overlays = [
            ("myfans", COLORS["MY_PLAN_BASE"], (0, (6, 4)), "plan"),
            ("myfans", COLORS["MY_POST_BAR"], (0, (2, 3)), "post"),
        ]
    else:  # CandFans
        main_color = COLORS["CA_LINE"]  # total
        overlays = [
            ("candfans", COLORS["CA_PLAN_BASE"], (0, (6, 4)), "plan"),
            ("candfans", COLORS["CA_POST_BAR"], (0, (2, 3)), "post"),
        ]

    buf = chart_daily_line_img(
        df_line,
        f"{title_prefix} 売上（{ym_label}）",
        main_color,
        height_px=line_h,
        overlays=overlays,
        x_mode=x_mode,
    )


    if buf is not None:
        st.image(buf, use_container_width=True)
    st.markdown("")

    bar_colors = (
        {"myfans": COLORS["MY_POST_BAR"], "candfans": COLORS["CA_POST_BAR"]}
        if title_prefix == "ALL"
        else (COLORS["MY_POST_BAR"] if title_prefix == "MyFans" else COLORS["CA_POST_BAR"])
    )

    if mobile_mode:
        plan_pie_img(df, f"{title_prefix}：プラン割合（売上）", height_px=bar_h)
        st.markdown("")
        g_post = top_bars_img(
            df,
            "post",
            f"{title_prefix}：投稿 TOP（売上）※URLのままは非表示",
            topn=10,
            color_spec=bar_colors,
            height_px=bar_h,
        )
    else:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            plan_pie_img(df, f"{title_prefix}：プラン割合（売上）", height_px=bar_h)
        with c2:
            g_post = top_bars_img(
                df,
                "post",
                f"{title_prefix}：投稿 TOP（売上）※URLのままは非表示",
                topn=10,
                color_spec=bar_colors,
                height_px=bar_h,
            )

    st.markdown("")
    render_post_ranking(g_post, title_prefix)

# =============================
# Tabs
# =============================
tab_all, tab_my, tab_ca = st.tabs(["ALL（累積）", "MyFans", "CandFans"])

with tab_all:
    st.markdown(
        '<div class="card"><div class="h1" style="font-size:1.25rem;">ALL（累積）</div><div class="muted">日別推移 / TOP / 明細</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    # 表示用（年・月フィルタ後）
    df_view_all = filter_by_year_month(
        df_all,
        selected_year,
        selected_month
    )

    section_overview(df_view_all, COLORS["ALL_LINE"], "ALL")

with tab_my:
    st.markdown(
        '<div class="card"><div class="h1" style="font-size:1.25rem;">MyFans</div><div class="muted">日別推移 / TOP / 明細</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    # ---- view df for MyFans (selected year/month) ----
    df_view_my = filter_by_year_month(df_my_all, selected_year, selected_month)

    section_overview(df_view_my, COLORS["MY_LINE"], "MyFans")

    if is_admin:
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        admin_fetch_myfans_titles(df_view_my)

with tab_ca:
    st.markdown(
        '<div class="card"><div class="h1" style="font-size:1.25rem;">CandFans</div><div class="muted">日別推移 / TOP / 明細</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    # ---- view df for CandFans (selected year/month) ----
    df_view_ca = filter_by_year_month(df_ca_all, selected_year, selected_month)

    section_overview(df_view_ca, COLORS["CA_LINE"], "CandFans")
