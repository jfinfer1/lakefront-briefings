#!/usr/bin/env python3
"""technicals.py HISTORY_CSV AS_OF_DATE(YYYY-MM-DD)
Applies the v24 live-row rule: rows dated AS_OF_DATE are excluded from technicals;
the newest prior row is the settle. Prints JSON."""
import csv, json, sys, datetime
def load(p):
    rows=[]
    with open(p, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            d=datetime.datetime.strptime(r['Date'],'%m/%d/%Y').date()
            g=lambda k: float(r[k].replace(',','')) if r[k] else None
            rows.append(dict(date=d,close=g('Price'),open=g('Open'),high=g('High'),low=g('Low')))
    rows.sort(key=lambda r:r['date']); return rows
def rsi(closes,n=14):
    gains=[max(closes[i]-closes[i-1],0) for i in range(1,len(closes))]
    losses=[max(closes[i-1]-closes[i],0) for i in range(1,len(closes))]
    ag=sum(gains[:n])/n; al=sum(losses[:n])/n
    for g,l in zip(gains[n:],losses[n:]):
        ag=(ag*(n-1)+g)/n; al=(al*(n-1)+l)/n
    return 100 if al==0 else 100-100/(1+ag/al)
def main(p, asof):
    asof=datetime.date.fromisoformat(asof)
    rows=load(p); live=[r for r in rows if r['date']==asof]
    hist=[r for r in rows if r['date']<asof]
    c=[r['close'] for r in hist]; last=hist[-1]
    sma=lambda n: round(sum(c[-n:])/n,2)
    w20=hist[-20:]; w60=hist[-60:]
    out=dict(settle_date=str(last['date']),settle=last['close'],prev_settle=c[-2],
      sma20=sma(20),sma50=sma(50),sma200=sma(200),rsi14=round(rsi(c[-250:]),1),
      high20=max(r['high'] for r in w20),low20=min(r['low'] for r in w20),
      high60=max(r['high'] for r in w60),low60=min(r['low'] for r in w60),
      high52w=max(r['high'] for r in hist[-252:]),low52w=min(r['low'] for r in hist[-252:]),
      session_row=(dict(date=str(live[0]['date']),last=live[0]['close'],change_vs_settle=round(live[0]['close']-last['close'],2)) if live else None))
    print(json.dumps(out,indent=1))
main(*sys.argv[1:])
