#!/usr/bin/env python3
"""运动周报 · 阶段 0：读取 index.html 导出的 JSON，输出统计。

用法：
    python stats.py 运动记录-2026-10-21.json
    python stats.py 记录.json --week 43          # 只算 2026 年第 43 周
    python stats.py 记录.json --week 2026-W43
    python stats.py 记录.json --all              # 全部记录，不按周筛
    python stats.py 记录.json --json             # 输出 JSON，给下一步喂模型

导出的记录格式（每条）：
    {"id": "...", "date": "2026-10-21", "type": "跑步",
     "minutes": 30, "distance": 5.0, "note": "...", "createdAt": 1761...}
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


# ---------- 读取 ----------

def load_records(paths: list[str]) -> list[dict]:
    """读入一个或多个导出文件，按 id 去重（后读的重复项丢弃）。"""
    seen: set[str] = set()
    out: list[dict] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            raise SystemExit(f"文件不存在：{p}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"{p} 不是合法 JSON：{e}")
        items = raw.get("records") if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            raise SystemExit(f"{p} 里没有记录数组")
        for r in items:
            if not isinstance(r, dict) or not r.get("date"):
                continue
            key = str(r.get("id") or f'{r["date"]}|{r.get("type")}|{r.get("minutes")}')
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
    return out


def parse_date(value: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


# ---------- 时间范围 ----------

def week_bounds(year: int, week: int) -> tuple[date, date]:
    """ISO 周的周一到周日。"""
    try:
        monday = date.fromisocalendar(year, week, 1)
    except ValueError:
        raise SystemExit(f"没有第 {week} 周（{year} 年）")
    return monday, monday + timedelta(days=6)


def resolve_week(spec: str | None) -> tuple[int, int]:
    """--week 43 / --week 2026-W43 / 不给 → 今天所在周。"""
    if not spec:
        iso = date.today().isocalendar()
        return iso.year, iso.week
    spec = spec.strip().upper().replace("W", "")
    if "-" in spec:
        y, w = spec.split("-", 1)
        return int(y), int(w)
    # 只给周数：落在今天这一年
    return date.today().isocalendar().year, int(spec)


# ---------- 统计 ----------

def compute(records: list[dict], start: date | None, end: date | None) -> dict:
    rows = []
    for r in records:
        d = parse_date(str(r.get("date", "")))
        if d is None:
            continue
        if start and d < start:
            continue
        if end and d > end:
            continue
        rows.append({
            "date": d,
            "type": str(r.get("type") or "未分类").strip() or "未分类",
            "minutes": int(float(r.get("minutes") or 0)),
            "distance": float(r["distance"]) if r.get("distance") not in (None, "") else None,
            "note": str(r.get("note") or "").strip(),
        })

    total_min = sum(x["minutes"] for x in rows)
    by_type: dict[str, dict[str, float]] = defaultdict(lambda: {"minutes": 0, "count": 0, "km": 0.0})
    per_day: dict[date, int] = defaultdict(int)
    for x in rows:
        by_type[x["type"]]["minutes"] += x["minutes"]
        by_type[x["type"]]["count"] += 1
        if x["distance"]:
            by_type[x["type"]]["km"] += x["distance"]
        per_day[x["date"]] += x["minutes"]

    longest = max(rows, key=lambda x: x["minutes"], default=None)
    active_days = len(per_day)

    # 连续天数：从区间末尾（不超过今天）往前数；末尾当天没记录就先退一天
    anchor = end or date.today()
    anchor = min(anchor, date.today())
    cursor = anchor if per_day.get(anchor) else anchor - timedelta(days=1)
    streak = 0
    while per_day.get(cursor):
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "range": {
            "start": (start or min(per_day, default=None)),
            "end": (end or date.today()),
        },
        "total_minutes": total_min,
        "count": len(rows),
        "active_days": active_days,
        "avg_minutes": round(total_min / active_days, 1) if active_days else 0,
        "streak_days": streak,
        "longest": ({"date": longest["date"].isoformat(), "type": longest["type"],
                     "minutes": longest["minutes"]} if longest else None),
        "by_type": sorted(
            ({"type": k, "minutes": v["minutes"], "count": v["count"], "km": round(v["km"], 1)}
             for k, v in by_type.items()),
            key=lambda x: (-x["minutes"], x["type"]),
        ),
        "daily": {d.isoformat(): m for d, m in sorted(per_day.items())},
        "records": [{**x, "date": x["date"].isoformat()} for x in rows],
    }


# ---------- 输出 ----------

def dwidth(text: str) -> int:
    """终端显示宽度：中日韩全角字符算 2 格。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - dwidth(text))


def human_min(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    if h and m:
        return f"{h} 小时 {m} 分"
    if h:
        return f"{h} 小时"
    return f"{m} 分钟"


def render_text(stats: dict, title: str) -> str:
    lines: list[str] = []
    rng = stats["range"]
    start, end = rng["start"], rng["end"]
    span = f"{start.isoformat()} ~ {end.isoformat()}" if start else "（无记录）"

    lines.append(title)
    lines.append(f"统计区间 {span}")
    lines.append("=" * 46)

    if not stats["count"]:
        lines.append("这段时间没有记录。")
        return "\n".join(lines)

    rows = [
        ("总时长", f'{stats["total_minutes"]} 分钟（{human_min(stats["total_minutes"])}）'),
        ("记录次数", f'{stats["count"]} 次'),
        ("运动天数", f'{stats["active_days"]} 天'),
        ("日均（按运动日）", f'{stats["avg_minutes"]} 分钟'),
        ("连续天数", f'{stats["streak_days"]} 天'),
    ]
    if stats["longest"]:
        lg = stats["longest"]
        rows.append(("最长一次", f'{lg["minutes"]} 分钟（{lg["type"]}，{lg["date"]}）'))

    label_w = max(dwidth(k) for k, _ in rows) + 4
    for label, value in rows:
        lines.append(f"{pad(label, label_w)}{value}")

    lines.append("")
    lines.append("按项目")
    peak = max(x["minutes"] for x in stats["by_type"]) or 1
    name_w = max(dwidth(x["type"]) for x in stats["by_type"]) + 2
    for item in stats["by_type"]:
        width = max(1, round(item["minutes"] / peak * 18))
        bar = "█" * width
        km = f' {item["km"]} km' if item["km"] else ""
        lines.append(f"  {pad(item['type'], name_w)}{item['minutes']:>5} 分  {pad(bar, 20)}{item['count']} 次{km}")

    lines.append("")
    lines.append("逐日")
    day_peak = max(stats["daily"].values()) or 1
    for day, minutes in stats["daily"].items():
        lines.append(f"  {day}  {minutes:>5} 分  {'█' * max(1, round(minutes / day_peak * 16))}")

    return "\n".join(lines)


# ---------- 入口 ----------

def find_latest() -> list[str]:
    """不给文件名时，自己去常见位置找最新的 运动记录-*.json。

    依次看：脚本所在目录、当前目录、系统下载目录。
    浏览器重复下载会留下 "记录-2026-10-22 (1).json" 这种名字，一并匹配。
    """
    here = Path(__file__).resolve().parent
    candidates: list[Path] = []
    for d in (here, Path.cwd(), Path.home() / "Downloads"):
        if d.is_dir():
            candidates.extend(d.glob("运动记录-*.json"))
    if not candidates:
        raise SystemExit(
            "没找到 运动记录-*.json。\n"
            "先从 D:\\运动记录\\index.html 点「导出 JSON」，再跑一次。"
        )
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f"（自动选用最新的记录文件：{newest}）", file=sys.stderr)
    return [str(newest)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="统计运动记录（读 index.html 导出的 JSON）")
    ap.add_argument("files", nargs="*", help="导出的 JSON 文件；不给就自动找最新的")
    ap.add_argument("--week", help="ISO 周，如 43 或 2026-W43；默认本周")
    ap.add_argument("--all", action="store_true", help="不按周筛，统计全部记录")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而不是文本")
    args = ap.parse_args(argv)

    records = load_records(args.files or find_latest())

    if args.all:
        start = end = None
        title = "运动记录 · 全部"
    else:
        year, week = resolve_week(args.week)
        start, end = week_bounds(year, week)
        title = f"运动记录 · {year}-W{week:02d}"

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    stats = compute(records, start, end)

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2, default=str))
    else:
        print(render_text(stats, title))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
