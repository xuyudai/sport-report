import json
with open("运动记录-2026-10-22.json",encoding="utf-8") as f:
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