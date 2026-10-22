import json
with open("运动记录-2026-10-22 (1).json",encoding="utf-8") as f:
    data =json.load(f)

print("一共",len(data),"条记录")
print("全部内容：",data)
total=0
for i,r in enumerate(data,start=1) :    
    print(f"第{i}次记录：{r['date']} {r['type']} {r['minutes']}分钟")
    total+=r['minutes']
print('总时长：',total)
if len(data)==0:
    print('这周没有记录')
else :
    n=len(data) 
    average=total/n
    average=round(average,1)
    print(f"平均每次{average}分钟")
longest=0
for r in data:
    if(r['minutes']>longest):
        longest=r['minutes']
print('最长的一段时间是：',longest)
by_type={}
for r in data:
    t=r['type']
    if t not in by_type:
        by_type[t]=0
    by_type[t]=by_type[t]+r['minutes']
for t in by_type:
    print(t,by_type[t],'分钟')