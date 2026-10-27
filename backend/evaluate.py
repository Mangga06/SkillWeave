"""Write real repeated-seed measurements from the current database snapshot."""
import argparse,json,statistics
from .database import SessionLocal
from .main import snapshot
from .optimizer import optimize
def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=5);p.add_argument('--org',type=int,default=1);p.add_argument('--output',default='docs/evaluation-results.json');a=p.parse_args()
    if not 2<=a.seeds<=100:p.error('Use 2–100 seeds')
    with SessionLocal() as db:s=snapshot(db,a.org)
    records=[]
    for seed in range(a.seeds):
        r=optimize(s,{'seed':seed,'population':30,'generations':40})
        for method,x in [('genetic',r),*r['baselines'].items()]:records.append({'method':method,'seed':seed,'fitness':x['fitness'],'coverage':x['breakdown']['coverage'],'unfilled':len(x['unfilled']),'imbalance':x['imbalance'],'violations':x['constraint_violations'],'runtime_ms':x['runtime_ms']})
    summary={}
    for method in ['genetic','greedy','random']:
        rows=[r for r in records if r['method']==method];summary[method]={k:{'mean':statistics.mean(r[k] for r in rows),'stdev':statistics.stdev(r[k] for r in rows)} for k in ['fitness','coverage','unfilled','imbalance','runtime_ms']}
    with open(a.output,'w',encoding='utf8') as f:json.dump({'source':'Current fictional/local database; not real-world impact evidence','records':records,'summary':summary},f,indent=2)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
