from sqlalchemy import select
from backend import models as m

def login(client,handle):return client.post('/api/v1/auth/login',json={'email':handle+'@demo.skillweave.test','password':'WeaveDemo!2026'})
def test_auth_session_and_logout(client):
    assert client.get('/api/v1/me').status_code==401
    assert client.post('/api/v1/auth/login',json={'email':'coordinator@demo.skillweave.test','password':'wrong'}).status_code==401
    assert login(client,'coordinator').status_code==200
    assert 'password_hash' not in client.get('/api/v1/me').json()
    token=client.cookies.get('skillweave_session')
    assert client.post('/api/v1/auth/logout').status_code==200
    client.cookies.set('skillweave_session',token)
    assert client.get('/api/v1/me').status_code==401
def test_role_and_tenant_isolation(client):
    login(client,'volunteer')
    assert client.get('/api/v1/admin/users').status_code==403
    assert client.post('/api/v1/optimization',json={}).status_code==403
    result=client.post('/api/v1/auth/register',json={'email':'new@example.test','name':'New Person','password':'safePassword!123'})
    assert result.status_code==201
    assert client.get('/api/v1/projects/1').status_code==404
    assert client.get('/api/v1/projects').json()==[]
def test_csrf_header(coordinator):
    assert coordinator.post('/api/v1/auth/logout',headers={'X-Requested-With':''}).status_code==403
def test_project_task_validation(coordinator):
    p=coordinator.post('/api/v1/projects',json={'name':'Test project','start':'2026-11-02T09:00','end':'2026-11-05T17:00'})
    assert p.status_code==201,p.text
    data={'name':'Welcome task','project_id':p.json()['id'],'start':'2026-11-02T09:00','end':'2026-11-02T12:00','hours':3,'minimum':1,'capacity':2,'priority':3}
    data['requirements']=[{'skill_id':99999,'level':3}]
    assert coordinator.post('/api/v1/tasks',json=data).status_code==422
    data['requirements']=[]
    t=coordinator.post('/api/v1/tasks',json=data);assert t.status_code==201,t.text
    data['capacity']=0;assert coordinator.post('/api/v1/tasks',json=data).status_code==422
    assert coordinator.delete('/api/v1/projects/'+str(p.json()['id'])).status_code==200
def test_profile_validation(client):
    login(client,'volunteer');p=client.get('/api/v1/me').json()
    p['skills']=[{'skill_id':1,'level':6}]
    assert client.put('/api/v1/me',json=p).status_code==422
    p=client.get('/api/v1/me').json();p['weekly_hours']=16
    assert client.put('/api/v1/me',json=p).status_code==200
    assert client.get('/api/v1/me').json()['weekly_hours']==16
def test_full_assignment_lifecycle(coordinator,database):
    c=coordinator
    r=c.post('/api/v1/optimization',json={'population':8,'generations':4,'seed':7})
    assert r.status_code==202,r.text
    rid=r.json()['id'];run=c.get(f'/api/v1/optimization/{rid}').json()
    assert run['status']=='completed',run
    assert run['result']['constraint_violations']==0
    assert c.get('/api/v1/assignments').json()==[]
    assert c.post(f'/api/v1/optimization/{rid}/publish').status_code==200
    assert c.post(f'/api/v1/optimization/{rid}/publish').status_code==409
    aa=c.get('/api/v1/assignments').json();assert aa
    target=next(a for a in aa if a['user_id']>=5)
    with database() as db:email=db.get(m.User,target['user_id']).email
    c.post('/api/v1/auth/logout');assert c.post('/api/v1/auth/login',json={'email':email,'password':'WeaveDemo!2026'}).status_code==200
    aid=target['id'];assert c.post(f'/api/v1/assignments/{aid}/respond',json={'status':'accepted'}).status_code==200
    assert c.post(f'/api/v1/assignments/{aid}/respond',json={'status':'declined'}).status_code==409
    h=c.post('/api/v1/hours',json={'assignment_id':aid,'hours':2});assert h.status_code==201,h.text
    assert c.post(f"/api/v1/hours/{h.json()['id']}/approve").status_code==403
    login(c,'coordinator');assert c.post(f"/api/v1/hours/{h.json()['id']}/approve").status_code==200
    with database() as db:t=db.get(m.Task,target['task_id']);leader=db.get(m.Project,t.project_id).leader_id;leader_email=db.get(m.User,leader).email
    assert c.post('/api/v1/auth/login',json={'email':leader_email,'password':'WeaveDemo!2026'}).status_code==200
    assert c.post(f"/api/v1/tasks/{target['task_id']}/progress",json={'percent':100,'note':'Verified test completion'}).status_code==200
def test_scenario_preview_and_stale_protection(coordinator):
    c=coordinator;before=c.get('/api/v1/assignments').json()
    r=c.post('/api/v1/optimization',json={'population':6,'generations':2,'scenario':{'kind':'capacity','task_id':2,'value':2}})
    assert r.status_code==202,r.text
    assert c.get('/api/v1/assignments').json()==before
    rid=r.json()['id'];assert c.get(f'/api/v1/optimization/{rid}').json()['status']=='completed'
    profile=c.get('/api/v1/me').json();profile['experience']+=1;c.put('/api/v1/me',json=profile)
    # Coordinator profile is not optimizer input; modify a project task to invalidate the snapshot instead.
    c.post('/api/v1/tasks/2/progress',json={'percent':10})
    assert c.post(f'/api/v1/optimization/{rid}/publish').status_code==409
def test_csv_and_import(coordinator):
    r=coordinator.get('/api/v1/reports/assignments.csv');assert r.status_code==200;assert 'text/csv' in r.headers['content-type']
    text='project_id,name,start,end,hours,minimum,capacity,priority\n99999,Bad task,2026-11-02T09:00,2026-11-02T12:00,3,1,2,3\n'
    r=coordinator.post('/api/v1/import/tasks',files={'file':('tasks.csv',text,'text/csv')})
    assert r.status_code==200;assert r.json()['imported']==0;assert r.json()['errors'][0]['row']==2
def test_formula_safety():
    from backend.main import safe_cell
    for s in ['=SUM(A1)','+1','-cmd','@formula','  =1']:
        assert safe_cell(s).startswith("'")
def test_admin_safeguard(client):
    login(client,'admin');u=client.get('/api/v1/me').json()
    assert client.put('/api/v1/admin/users/'+str(u['id']),json={'active':False,'role':'volunteer'}).status_code==409
def test_other_leader_rejected(client,database):
    login(client,'leader')
    with database() as db:p=db.scalar(select(m.Project).where(m.Project.leader_id!=3,m.Project.org_id==1))
    assert client.get('/api/v1/projects/'+str(p.id)).status_code==403
def test_organization_invite_registration_and_reuse(coordinator):
    c=coordinator
    invitation=c.post('/api/v1/organization/invitations',json={'email':'invited@example.test','role':'volunteer'})
    assert invitation.status_code==201
    token=invitation.json()['token']
    data={'email':'invited@example.test','name':'Invited Person','password':'safePassword!123','invite_token':token}
    r=c.post('/api/v1/auth/register',json=data);assert r.status_code==201,r.text;assert r.json()['org_id']==1;assert r.json()['role']=='volunteer'
    assert len(c.get('/api/v1/projects').json())>=4
    assert c.post('/api/v1/organization/invitations',json={'email':'other@example.test','role':'admin'}).status_code==422
    assert c.post('/api/v1/organization/invitations',json={'email':'other@example.test','role':'volunteer'}).status_code==403
    data['email']='different@example.test';assert c.post('/api/v1/auth/register',json=data).status_code==422
def test_existing_personal_workspace_can_join(coordinator):
    c=coordinator
    assert c.post('/api/v1/auth/register',json={'email':'new@example.test','name':'New Person','password':'safePassword!123'}).status_code==201
    login(c,'coordinator')
    token=c.post('/api/v1/organization/invitations',json={'email':'new@example.test','role':'volunteer'}).json()['token']
    assert c.post('/api/v1/auth/login',json={'email':'new@example.test','password':'safePassword!123'}).status_code==200
    assert c.post('/api/v1/organization/join',json={'token':token}).status_code==200
    assert c.get('/api/v1/me').json()['org_id']==1
    assert c.post('/api/v1/organization/join',json={'token':token}).status_code==422
def test_completed_work_is_preserved_on_new_publication(coordinator,database):
    c=coordinator
    with database() as db:
        t=db.get(m.Task,1);t.status='completed';t.progress=100
        a=m.Assignment(task_id=1,user_id=5,status='completed');db.add(a);db.commit();ids=[a.id]
    r=c.post('/api/v1/optimization',json={'population':6,'generations':2});assert r.status_code==202
    rid=r.json()['id'];run=c.get(f'/api/v1/optimization/{rid}').json()
    assert all(t['status']!='completed' for t in run['snapshot']['tasks'])
    published=c.post(f'/api/v1/optimization/{rid}/publish');assert published.status_code==200,published.text
    with database() as db:assert all(db.get(m.Assignment,aid).status=='completed' for aid in ids)
