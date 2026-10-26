import stats
import sys
import os
import requests
week=int (sys.argv[1]) if len(sys.argv) > 1 else 43
records=stats.load_records(stats.find_latest())
start,end=stats.week_bounds(2026,week)
data=stats.compute(records,start,end)
if data['count']==0:
    print(f"第{week}周没有记录，先去记上一笔再来。")
    sys.exit(0)
print(data['total_minutes'],"分钟",data['count'],'次')
lines=[]
lines.append(f"本周({data['range']['start']})到{data['range']['end']}运动情况：")
lines.append(f"-运动总时长{data['total_minutes']}分钟")
lines.append(f"-运动{data['active_days']}天,共{data['count']}次")
for item in data['by_type']:
    lines.append(f"-{item['type']}{item['minutes']}分钟{item['count']}次")
lines.append(f"-连续运动{data['streak_days']}天")
if data['longest']:
    lines.append(f"-最长的一次{data['longest']['minutes']}分钟({data['longest']['type']})")
prompt="\n".join(lines)
print(prompt)
key=os.environ["DEEPSEEK_API_KEY"]
system='你是一个健身教练,根据数据写一份简短周报,300字以内,语气平实，最后给一条具体建议'
resp=requests.post(
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization":f"Bearer {key}"},
    json={
        "model":"deepseek-chat",
        "messages":[
            {"role":"system","content":system},
            {"role":"user","content":prompt},
        ],
    },
    timeout=60
)
text = resp.json()["choices"][0]["message"]["content"]
print(text)
with open(f"周报-2026-W{week}.md","w",encoding='utf-8') as f:
    f.write(text)