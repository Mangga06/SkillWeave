import copy
import pytest
from backend.optimizer import memberships,triangle,fuzzy,optimize,eligible,DEFAULT_WEIGHTS

def fixture():
    vs=[{'id':i,'name':str(i),'active':True,'weekly_hours':6,'experience':4,'interests':['Community'],'learning_goals':['1'],'skills':{'1':{'level':4,'verified':True}},'availability':[{'start':'2026-11-02T09:00:00','end':'2026-11-02T17:00:00'}]} for i in range(1,7)]
    ts=[{'id':i,'name':str(i),'category':'Community','start':f'2026-11-02T{9+i:02}:00:00','end':f'2026-11-02T{12+i:02}:00:00','hours':3,'capacity':2,'minimum':2,'priority':i,'difficulty':3,'requirements':[{'skill_id':1,'level':3,'mandatory':True,'verified':True}]} for i in [1,2]]
    return {'tasks':ts,'volunteers':vs,'assignments':[]}
def test_memberships():
    assert memberships(0)=={'low':1,'medium':0,'high':0}
    assert memberships(.5)['medium']==1
    assert memberships(1)['high']==1
    assert triangle(.25,0,.5,1)==.5
@pytest.mark.parametrize('p',[0,.2,.5,.8,1])
def test_fuzzy_bounds(p):
    r=fuzzy(p,.7,1,.6,.5);assert 0<=r['score']<=1;assert r['rules'];assert r['memberships']
def test_rules_are_directional():
    assert fuzzy(1,1,1,.4,1)['score']>fuzzy(.1,.1,.1,1,.1)['score']
def test_qualifications_and_availability():
    s=fixture();v=s['volunteers'][0];t=s['tasks'][0]
    assert eligible(v,t)[0]
    v['skills']['1']['verified']=False;assert not eligible(v,t)[0]
    v['skills']['1']['verified']=True;v['availability']=[];assert not eligible(v,t)[0]
def test_ga_feasibility_baselines_reproducibility():
    s=fixture();config={'population':12,'generations':8,'seed':21}
    a=optimize(s,config);b=optimize(s,config)
    assert a['allocation']==b['allocation'];assert a['fitness']==b['fitness']
    assert len(a['history'])==8;assert a['history'][-1]['best']>=a['history'][0]['best']
    for allocation in [a['allocation'],*[r['allocation'] for r in a['baselines'].values()]]:
        ids=[uid for team in allocation.values() for uid in team]
        assert len(ids)==len(set(ids)) # tasks overlap
        assert all(len(team)<=2 for team in allocation.values())
    assert a['constraint_violations']==0;assert set(a['baselines'])=={'greedy','random'}
def test_locked_preservation():
    s=fixture();s['assignments']=[{'task_id':1,'user_id':1,'status':'accepted','locked':False}]
    r=optimize(s,{'population':8,'generations':3});assert 1 in r['allocation'][1]
    s['volunteers'][0]['active']=False
    with pytest.raises(ValueError,match='locked'):optimize(s,{'population':8,'generations':3})
def test_infeasible_returns_gaps():
    s=fixture()
    for v in s['volunteers']:v['skills']={}
    r=optimize(s,{'population':6,'generations':2})
    assert len(r['unfilled'])==2;assert r['breakdown']['coverage']==0
    assert r['exclusions'];assert r['constraint_violations']==0
def test_weekly_budget_and_mutation_repair():
    s=fixture()
    for v in s['volunteers']:v['weekly_hours']=2
    r=optimize(s,{'population':12,'generations':5,'mutation':1})
    assert not any(r['allocation'].values())
def test_preview_does_not_mutate():
    from backend.main import apply_scenario
    s=fixture();old=copy.deepcopy(s);changed=apply_scenario(s,{'kind':'withdrawal','user_id':1})
    assert s==old;assert not changed['volunteers'][0]['active']
def test_declined_invitation_is_not_repeated():
    s=fixture();s['assignments']=[{'task_id':1,'user_id':1,'status':'declined','locked':False}]
    r=optimize(s,{'population':8,'generations':3})
    assert 1 not in r['allocation'][1]
    assert any(e['user_id']==1 and e['task_id']==1 and 'declined' in e['reason'] for e in r['exclusions'])
