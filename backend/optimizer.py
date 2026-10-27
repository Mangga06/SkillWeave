"""Deterministic seeded GA; all algorithms share feasibility repair and evaluation."""
import random
import time
import math
import statistics
from datetime import datetime

ACTIVE = {'invited','accepted','confirmed','in_progress','completed'}
DEFAULT_WEIGHTS = {'coverage': .30, 'staffing': .20, 'suitability': .15, 'fairness': .15, 'preference': .05, 'learning': .05, 'stability': .10}

def triangle(x, a, b, c):
    if x == b: return 1.0
    if x <= a or x >= c: return 0.0
    return (x-a)/(b-a) if x < b else (c-x)/(c-b)

def memberships(x):
    x = max(0, min(1, x))
    return {'low': max(0, 1-2*x), 'medium': triangle(x, 0, .5, 1), 'high': max(0, 2*x-1)}

def fuzzy(proficiency, experience, availability, difficulty, preference):
    inputs = {k: memberships(v) for k,v in dict(proficiency=proficiency,experience=experience,availability=availability,difficulty=difficulty,preference=preference).items()}
    p,e,a,d,f = [inputs[k] for k in ('proficiency','experience','availability','difficulty','preference')]
    rules = [
        ('Availability low → low suitability', a['low'], 'low'),
        ('Proficiency low → low suitability', p['low'], 'low'),
        ('Proficiency high AND experience high AND availability high → high', min(p['high'],e['high'],a['high']), 'high'),
        ('Proficiency medium AND difficulty high → low', min(p['medium'],d['high']), 'low'),
        ('Proficiency medium AND availability high → medium', min(p['medium'],a['high']), 'medium'),
        ('Proficiency high AND availability high → high', min(p['high'],a['high']), 'high'),
        ('Preference high AND proficiency medium → medium', min(f['high'],p['medium']), 'medium'),
        ('Availability medium → medium', a['medium'], 'medium'),
    ]
    # Mamdani min implication, max aggregation, numerical centroid on [0,1].
    area = moment = 0
    for i in range(101):
        x = i/100
        output = memberships(x)
        mu = max(min(strength, output[label]) for _,strength,label in rules)
        area += mu; moment += mu*x
    return {'score': round(moment/area if area else .5, 4), 'memberships': inputs, 'rules': [{'rule':name,'strength':round(s,3)} for name,s,_ in rules if s > 0], 'warnings': ['Skills are self-reported unless marked verified.']}

def overlap(a,b):
    return a['start'] < b['end'] and b['start'] < a['end']

def eligible(v,t):
    if not v['active']: return False, 'Volunteer unavailable or deactivated'
    if not any(w['start'] <= t['start'] and w['end'] >= t['end'] for w in v['availability']): return False, 'No availability window covers this task'
    for r in t['requirements']:
        s = v['skills'].get(str(r['skill_id']), {})
        if r['mandatory'] and (s.get('level',0) < r['level'] or (r['verified'] and not s.get('verified'))):
            return False, 'Mandatory proficiency or verified qualification missing'
    return True, ''

def suitability(v,t):
    req = t['requirements']
    prof = sum(min(1,v['skills'].get(str(r['skill_id']),{}).get('level',0)/r['level']) for r in req)/len(req) if req else .7
    return fuzzy(prof,min(1,v['experience']/5),1,t['difficulty']/5,1 if t['category'] in v['interests'] else .5)

def optimize(snapshot, config):
    started = time.perf_counter()
    rng = random.Random(config.get('seed',42))
    tasks = snapshot['tasks']; volunteers = snapshot['volunteers']
    vm = {v['id']: v for v in volunteers}; tm = {t['id']:t for t in tasks}
    current = {(a['task_id'],a['user_id']) for a in snapshot['assignments'] if a['status'] in ACTIVE}
    locks = {(a['task_id'],a['user_id']) for a in snapshot['assignments'] if a['status'] in ACTIVE and (a['locked'] or a['status'] in {'accepted','confirmed','in_progress','completed'})}
    rejected = {(a['task_id'],a['user_id']) for a in snapshot['assignments'] if a['status'] in {'declined','withdrawn'}}
    candidates = {t['id']:[v['id'] for v in volunteers if eligible(v,t)[0] and (t['id'],v['id']) not in rejected] for t in tasks}
    fits = {(t['id'],v['id']):suitability(v,t) for t in tasks for v in volunteers if v['id'] in candidates[t['id']]}
    for tid,uid in locks:
        if tid not in tm or uid not in vm or uid not in candidates[tid]:
            raise ValueError('Scenario conflicts with a locked or confirmed assignment. Resolve the lock explicitly first.')
    weights = config.get('weights') or DEFAULT_WEIGHTS
    total_weight = sum(weights.values())
    if total_weight <= 0: raise ValueError('At least one fitness weight must be positive')

    def feasible(plan,tid,uid):
        t = tm[tid]; v = vm[uid]
        if uid not in candidates[tid] or uid in plan[tid] or len(plan[tid]) >= t['capacity']: return False
        assigned = [tm[k] for k,team in plan.items() if uid in team]
        if any(overlap(t,other) for other in assigned): return False
        # ISO weeks are separate hour budgets; cross-week tasks count in their start week.
        week = datetime.fromisoformat(t['start']).isocalendar()[:2]
        hours = sum(x['hours'] for x in assigned if datetime.fromisoformat(x['start']).isocalendar()[:2] == week)
        return hours + t['hours'] <= v['weekly_hours']

    def repair(raw, fill=False, greedy=False):
        plan = {t['id']:[] for t in tasks}
        for tid,uid in sorted(locks):
            if not feasible(plan,tid,uid): raise ValueError('Locked assignments violate capacity, overlap, or weekly hours')
            plan[tid].append(uid)
        order = sorted(tasks,key=lambda t:-t['priority'])
        if not greedy: rng.shuffle(order)
        for t in order:
            tid = t['id']; pool = list(dict.fromkeys(raw.get(tid,[])))
            if fill:
                rest = [uid for uid in candidates[tid] if uid not in pool]
                if greedy: rest.sort(key=lambda uid:-fits[tid,uid]['score'])
                else: rng.shuffle(rest)
                pool += rest
            for uid in pool:
                if uid in vm and feasible(plan,tid,uid): plan[tid].append(uid)
        return plan

    def evaluate(plan):
        pairs = {(tid,uid) for tid,team in plan.items() for uid in team}
        priorities = sum(t['priority'] for t in tasks) or 1
        staffing = sum(t['priority']*min(1,len(plan[t['id']])/t['minimum']) for t in tasks)/priorities
        covered = required = 0
        gaps = []
        for t in tasks:
            for r in t['requirements']:
                required += 1
                yes = any(vm[uid]['skills'].get(str(r['skill_id']),{}).get('level',0)>=r['level'] and (not r['verified'] or vm[uid]['skills'].get(str(r['skill_id']),{}).get('verified')) for uid in plan[t['id']])
                covered += int(yes)
                if not yes: gaps.append({'task_id':t['id'],'skill_id':r['skill_id']})
        loads = {v['id']:sum(tm[tid]['hours'] for tid,uid in pairs if uid==v['id']) for v in volunteers}
        # Normalize per weekly budget aggregated across weeks represented by the input.
        weeks = max(1,len({datetime.fromisoformat(t['start']).isocalendar()[:2] for t in tasks}))
        ratios = [loads[v['id']]/(v['weekly_hours']*weeks) if v['weekly_hours'] else 0 for v in volunteers]
        imbalance = statistics.pstdev(ratios) if ratios else 0
        preference = sum(tm[tid]['category'] in vm[uid]['interests'] for tid,uid in pairs)/max(1,len(pairs))
        learning = sum(any(str(r['skill_id']) in vm[uid]['learning_goals'] and vm[uid]['skills'].get(str(r['skill_id']),{}).get('level',0)>=r['level'] for r in tm[tid]['requirements']) for tid,uid in pairs)/max(1,len(pairs))
        breakdown = {'coverage':covered/required if required else 1,'staffing':staffing,'suitability':sum(fits[p]['score'] for p in pairs)/max(1,len(pairs)), 'fairness':max(0,1-imbalance),'preference':preference,'learning':learning,'stability':len(pairs & current)/len(current) if current else 1}
        score = sum(weights.get(k,0)*v for k,v in breakdown.items())/total_weight
        violations=0
        for t in tasks:
            team=plan[t['id']]
            violations+=max(0,len(team)-t['capacity'])+len(team)-len(set(team))
            violations+=sum(uid not in candidates[t['id']] for uid in team)
        violations+=len(locks-pairs)
        for v in volunteers:
            assigned=[tm[tid] for tid,uid in pairs if uid==v['id']]
            violations+=sum(overlap(a,b) for i,a in enumerate(assigned) for b in assigned[i+1:])
            week_hours={}
            for t in assigned:
                week=datetime.fromisoformat(t['start']).isocalendar()[:2]
                week_hours[week]=week_hours.get(week,0)+t['hours']
            violations+=sum(h>v['weekly_hours'] for h in week_hours.values())
        return {'fitness':round(score,5),'breakdown':breakdown,'missing_skills':gaps,'workload':loads,'imbalance':imbalance,'constraint_violations':violations,'changed_assignments':len(pairs ^ current),'unfilled':[{'task_id':t['id'],'missing':max(0,t['minimum']-len(plan[t['id']]))} for t in tasks if len(plan[t['id']]) < t['minimum']]}

    baselines = {}
    for method in ['greedy','random']:
        ts = time.perf_counter(); plan = repair({},True,method=='greedy')
        baselines[method] = {**evaluate(plan),'runtime_ms':round((time.perf_counter()-ts)*1000,2),'allocation':plan,'generations':0}
    size = config.get('population',40); generations = config.get('generations',50)
    population = [repair({},True) for _ in range(size-1)] + [baselines['greedy']['allocation']]
    history=[]
    for gen in range(generations):
        ranked = sorted(population,key=lambda p:evaluate(p)['fitness'],reverse=True)
        history.append({'generation':gen+1,'best':evaluate(ranked[0])['fitness'],'mean':sum(evaluate(p)['fitness'] for p in population)/size})
        next_pop = ranked[:2]
        def select(): return max(rng.sample(population,3),key=lambda p:evaluate(p)['fitness'])
        while len(next_pop) < size:
            a,b = select(),select()
            child = {t['id']:list((a if rng.random()<.5 else b)[t['id']]) for t in tasks}
            if rng.random() < config.get('mutation',.25) and tasks:
                tid = rng.choice(tasks)['id']
                child[tid] = rng.sample(candidates[tid],min(len(candidates[tid]),rng.randint(0,tm[tid]['capacity'])))
            next_pop.append(repair(child,fill=rng.random()<.3))
        population=next_pop
    best = max(population,key=lambda p:evaluate(p)['fitness'])
    metrics = evaluate(best)
    return {**metrics,'allocation':best,'history':history,'baselines':baselines,'weights':weights,'runtime_ms':round((time.perf_counter()-started)*1000,2),'generations':generations,'explanations':[{'task_id':tid,'user_id':uid,**fits[tid,uid]} for tid,team in best.items() for uid in team], 'exclusions':[{'task_id':t['id'],'user_id':v['id'],'reason':'Previously declined or withdrawn from this task' if (t['id'],v['id']) in rejected else eligible(v,t)[1]} for t in tasks for v in volunteers if v['id'] not in candidates[t['id']]],'warnings':['Minimum staffing and team skill coverage are soft objectives; inspect all unfilled responsibilities.','Fairness measures dispersion of assigned / available hours, not every dimension of fairness.','Learning matches require existing minimum proficiency; supervised stretch roles are not modeled.']}
