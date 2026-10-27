import os, secrets, hashlib, time, csv, io, copy, logging
from collections import defaultdict, deque
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, Request, Response, BackgroundTasks, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session as DB
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from .database import SessionLocal, get_db, now, engine
from . import models as m, schemas as s
from .optimizer import optimize, ACTIVE, eligible, overlap

app = FastAPI(title='SkillWeave API', version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://127.0.0.1:5173,http://localhost:5173').split(','),allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Content-Type','X-Requested-With'])
ph = PasswordHasher()
COOKIE='skillweave_session'
secure = os.getenv('ENVIRONMENT','development') == 'production'
attempts=defaultdict(deque)
def fail(code,detail): raise HTTPException(code,detail)
def hashed(token): return hashlib.sha256(token.encode()).hexdigest()
def audit(db,u,action,detail=''):
    db.add(m.AuditLog(org_id=u.org_id,actor_id=u.id,action=action,detail=detail))
def notify(db,uid,text): db.add(m.Notification(user_id=uid,text=text))
def public(obj): return {c.name:getattr(obj,c.name) for c in obj.__table__.columns if c.name not in {'password_hash','token_hash'}}
def user(request: Request, db: DB=Depends(get_db)):
    token=request.cookies.get(COOKIE,'')
    session=db.get(m.Session,hashed(token))
    if not session or session.expires < now(): fail(401,'Please sign in')
    u=db.get(m.User,session.user_id)
    if not u or not u.active: fail(401,'Account inactive')
    if request.method not in {'GET','HEAD','OPTIONS'} and request.headers.get('X-Requested-With')!='SkillWeave': fail(403,'Missing request protection header')
    return u
def roles(u,*allowed):
    if u.role not in allowed: fail(403,'Your role cannot perform this action')
def project(db,u,pid):
    p=db.get(m.Project,pid)
    if not p or (u.role!='admin' and p.org_id!=u.org_id): fail(404,'Project not found')
    if u.role=='leader' and p.leader_id!=u.id: fail(403,'Project is not assigned to you')
    return p
def task(db,u,tid):
    t=db.get(m.Task,tid)
    if not t: fail(404,'Task not found')
    project(db,u,t.project_id); return t
def assignment(db,u,aid):
    a=db.get(m.Assignment,aid)
    if not a: fail(404,'Assignment not found')
    task(db,u,a.task_id)
    if u.role=='volunteer' and a.user_id!=u.id: fail(403,'This assignment belongs to another volunteer')
    return a
def throttle(request):
    key=request.client.host; q=attempts[key]; ts=time.monotonic()
    while q and q[0]<ts-60:q.popleft()
    if len(q)>=20: fail(429,'Too many attempts. Try again in a minute.')
    q.append(ts)
def start_session(db,u,response):
    token=secrets.token_urlsafe(40)
    db.add(m.Session(token_hash=hashed(token),user_id=u.id,expires=now()+timedelta(hours=12)))
    response.set_cookie(COOKIE,token,httponly=True,secure=secure,samesite='lax',max_age=43200,path='/')
def valid_invite(db,token,email):
    invite=db.scalar(select(m.OrganizationInvitation).where(m.OrganizationInvitation.token_hash==hashed(token)))
    if not invite or invite.used or invite.expires<now() or invite.email!=email:fail(422,'Invitation is invalid, expired, already used, or belongs to another email')
    org=db.get(m.Organization,invite.org_id)
    if not org or not org.active:fail(422,'Organization is inactive')
    return invite

@app.get('/api/v1/health')
def health(db: DB=Depends(get_db)):
    db.execute(select(1)); return {'status':'ok','database':'connected','email':'not configured','demo':os.getenv('DEMO_MODE','false')=='true'}
@app.post('/api/v1/auth/login')
def login(data:s.Login,request:Request,response:Response,db:DB=Depends(get_db)):
    throttle(request); u=db.scalar(select(m.User).where(m.User.email==data.email))
    # Always verify a hash to avoid a fast path that reveals account existence.
    try: valid=ph.verify(u.password_hash if u else DUMMY_HASH,data.password)
    except (VerifyMismatchError,InvalidHashError): valid=False
    if not u or not valid or not u.active: fail(401,'Invalid email or password')
    start_session(db,u,response); audit(db,u,'auth.login'); db.commit(); return public(u)
DUMMY_HASH=ph.hash(secrets.token_urlsafe(30))
@app.post('/api/v1/auth/register',status_code=201)
def register(data:s.Register,request:Request,response:Response,db:DB=Depends(get_db)):
    throttle(request)
    if db.scalar(select(m.User).where(m.User.email==data.email)): fail(409,'Email already registered')
    # A new registration owns a new workspace; it cannot join a tenant by supplying an ID.
    invite=valid_invite(db,data.invite_token,data.email) if data.invite_token else None
    if invite:org=db.get(m.Organization,invite.org_id);invite.used=True
    else:org=m.Organization(name=f'{data.name} workspace'); db.add(org); db.flush()
    u=m.User(email=data.email,name=data.name,password_hash=ph.hash(data.password),org_id=org.id,role=invite.role if invite else 'volunteer')
    db.add(u);db.flush();db.add(m.Membership(user_id=u.id,org_id=org.id));start_session(db,u,response);audit(db,u,'auth.register');db.commit();return public(u)
@app.post('/api/v1/auth/logout')
def logout(request:Request,response:Response,u=Depends(user),db:DB=Depends(get_db)):
    db.execute(delete(m.Session).where(m.Session.token_hash==hashed(request.cookies.get(COOKIE,''))));db.commit();response.delete_cookie(COOKIE);return {'ok':True}
@app.post('/api/v1/auth/reset-request')
def reset_request(data:s.Login,request:Request,db:DB=Depends(get_db)):
    throttle(request);u=db.scalar(select(m.User).where(m.User.email==data.email))
    result={'message':'If the account exists, reset instructions will be available through the configured delivery channel.'}
    if u:
        token=secrets.token_urlsafe(40);db.add(m.ResetToken(token_hash=hashed(token),user_id=u.id,expires=now()+timedelta(minutes=15)));db.commit()
        # Development-only local terminal delivery; never return tokens to arbitrary callers.
        if not secure: logging.warning('LOCAL DEVELOPMENT password reset for %s: %s',u.email,token)
    return result
@app.post('/api/v1/auth/reset')
def reset(data:dict,request:Request,db:DB=Depends(get_db)):
    throttle(request);token=db.get(m.ResetToken,hashed(str(data.get('token',''))));pw=str(data.get('password',''))
    if not token or token.expires<now() or not 10<=len(pw)<=128: fail(400,'Invalid token or password must contain 10–128 characters')
    u=db.get(m.User,token.user_id);u.password_hash=ph.hash(pw);db.execute(delete(m.Session).where(m.Session.user_id==u.id));db.delete(token);audit(db,u,'auth.password_reset');db.commit();return {'ok':True}

def profile_data(db,u,viewer=None):
    stmt=select(m.Assignment,m.Task,m.Project).join(m.Task,m.Assignment.task_id==m.Task.id).join(m.Project,m.Task.project_id==m.Project.id).where(m.Assignment.user_id==u.id,m.Project.org_id==u.org_id).order_by(m.Project.start.desc(),m.Task.start)
    if viewer and viewer.role=='leader' and viewer.id!=u.id:stmt=stmt.where(m.Project.leader_id==viewer.id)
    history={}
    for a,t,p in db.execute(stmt):
        entry=history.setdefault(p.id,{'project_id':p.id,'name':p.name,'category':p.category,'status':p.status,'start':p.start,'end':p.end,'approved_hours':0,'tasks':[]})
        h=db.scalar(select(m.HourRecord).where(m.HourRecord.assignment_id==a.id))
        if h and h.approved:entry['approved_hours']+=h.hours
        entry['tasks'].append({'name':t.name,'status':a.status,'progress':t.progress})
    return {**public(u),'skills':[public(x) for x in db.scalars(select(m.VolunteerSkill).where(m.VolunteerSkill.user_id==u.id))], 'availability':[public(x) for x in db.scalars(select(m.Availability).where(m.Availability.user_id==u.id))], 'work_history':list(history.values())}
@app.get('/api/v1/me')
def me(u=Depends(user),db:DB=Depends(get_db)): return profile_data(db,u)
@app.put('/api/v1/me')
def update_profile(data:s.Profile,u=Depends(user),db:DB=Depends(get_db)):
    ids=[x.skill_id for x in data.skills]
    if len(ids)!=len(set(ids)) or any(not db.get(m.Skill,k) for k in ids): fail(422,'Invalid or duplicate skill')
    existing={x.skill_id:x for x in db.scalars(select(m.VolunteerSkill).where(m.VolunteerSkill.user_id==u.id))}
    for k,v in data.model_dump(exclude={'skills','availability'}).items():setattr(u,k,v)
    db.execute(delete(m.VolunteerSkill).where(m.VolunteerSkill.user_id==u.id));db.execute(delete(m.Availability).where(m.Availability.user_id==u.id))
    for x in data.skills:
        old=existing.get(x.skill_id)
        db.add(m.VolunteerSkill(user_id=u.id,**x.model_dump(),verified=bool(old and old.verified and old.level==x.level)))
    for w in data.availability:db.add(m.Availability(user_id=u.id,**w.model_dump()))
    audit(db,u,'profile.update');db.commit();return profile_data(db,u)
@app.get('/api/v1/skills')
def skills(u=Depends(user),db:DB=Depends(get_db)):return [public(x) for x in db.scalars(select(m.Skill).order_by(m.Skill.name))]
@app.post('/api/v1/skills',status_code=201)
def add_skill(data:dict,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin');name=str(data.get('name','')).strip()
    if not 2<=len(name)<=80:fail(422,'Skill name must contain 2–80 characters')
    if db.scalar(select(m.Skill).where(m.Skill.name==name)):fail(409,'Skill already exists')
    x=m.Skill(name=name,category=str(data.get('category','Community'))[:80]);db.add(x);audit(db,u,'skill.create',name);db.commit();return public(x)
@app.get('/api/v1/volunteers')
def volunteers(q:str='',offset:int=0,limit:int=50,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator','leader')
    stmt=select(m.User).where(m.User.org_id==u.org_id,m.User.role.in_(['volunteer','leader']),m.User.name.ilike(f'%{q}%'))
    if u.role=='leader':
        permitted=select(m.Assignment.user_id).join(m.Task).join(m.Project).where(m.Project.leader_id==u.id)
        stmt=stmt.where(m.User.id.in_(permitted))
    return [profile_data(db,v,u) for v in db.scalars(stmt.offset(max(0,offset)).limit(max(1,min(100,limit))))]
@app.get('/api/v1/organization')
def organization(u=Depends(user),db:DB=Depends(get_db)):return public(db.get(m.Organization,u.org_id))
@app.put('/api/v1/organization')
def org_update(data:dict,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');o=db.get(m.Organization,u.org_id)
    name=str(data.get('name','')).strip()
    if not 2<=len(name)<=150:fail(422,'Organization name must contain 2–150 characters')
    o.name=name;o.description=str(data.get('description',''))[:5000];audit(db,u,'organization.update');db.commit();return public(o)
@app.post('/api/v1/organization/invitations',status_code=201)
def invite_member(data:s.InviteIn,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator')
    email=data.email
    role=data.role
    if role not in {'leader','volunteer'}:fail(422,'Invite only volunteers or team leaders')
    token=secrets.token_urlsafe(40)
    invitation=m.OrganizationInvitation(org_id=u.org_id,email=email,role=role,token_hash=hashed(token),expires=now()+timedelta(days=7))
    db.add(invitation);audit(db,u,'membership.invite',email);db.commit()
    return {'id':invitation.id,'token':token,'email':email,'role':role,'expires':invitation.expires,'delivery':'Share this single-use code with the named recipient. Email delivery is not configured.'}
@app.post('/api/v1/organization/join')
def join_member(data:dict,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'volunteer');invite=valid_invite(db,str(data.get('token','')),u.email)
    if invite.org_id==u.org_id:fail(409,'You already belong to this organization')
    if db.scalar(select(func.count()).select_from(m.User).where(m.User.org_id==u.org_id))!=1 or db.scalar(select(m.Project.id).where(m.Project.org_id==u.org_id)) or db.scalar(select(m.Assignment.id).where(m.Assignment.user_id==u.id)) or db.scalar(select(m.Application.id).where(m.Application.user_id==u.id)):
        fail(409,'Only an unused personal workspace can join by code. Existing organization transfers need administrator review.')
    u.org_id=invite.org_id;u.role=invite.role;invite.used=True
    membership=db.scalar(select(m.Membership).where(m.Membership.user_id==u.id));membership.org_id=invite.org_id
    notify(db,u.id,'You joined '+db.get(m.Organization,invite.org_id).name);audit(db,u,'membership.join');db.commit();return public(u)
@app.get('/api/v1/projects')
def projects(q:str='',offset:int=0,limit:int=50,u=Depends(user),db:DB=Depends(get_db)):
    stmt=select(m.Project).where(m.Project.org_id==u.org_id,m.Project.name.ilike(f'%{q}%'))
    if u.role=='leader':stmt=stmt.where(m.Project.leader_id==u.id)
    return [public(p) for p in db.scalars(stmt.order_by(m.Project.start).offset(max(0,offset)).limit(max(1,min(100,limit))))]
def check_project(data,db,u):
    if data.leader_id:
        leader=db.get(m.User,data.leader_id)
        if not leader or leader.org_id!=u.org_id or leader.role!='leader' or not leader.active:fail(422,'Select an active team leader from your organization')
@app.post('/api/v1/projects',status_code=201)
def create_project(data:s.ProjectIn,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');check_project(data,db,u);p=m.Project(org_id=u.org_id,**data.model_dump());db.add(p);audit(db,u,'project.create',data.name);db.commit();return public(p)
@app.get('/api/v1/projects/{pid}')
def get_project(pid:int,u=Depends(user),db:DB=Depends(get_db)):return public(project(db,u,pid))
@app.put('/api/v1/projects/{pid}')
def edit_project(pid:int,data:s.ProjectIn,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');p=project(db,u,pid);check_project(data,db,u)
    if any(t.start<data.start or t.end>data.end for t in db.scalars(select(m.Task).where(m.Task.project_id==pid))):fail(422,'Project dates must contain all task windows')
    for k,v in data.model_dump().items():setattr(p,k,v)
    audit(db,u,'project.update',str(pid));db.commit();return public(p)
@app.delete('/api/v1/projects/{pid}')
def cancel_project(pid:int,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');p=project(db,u,pid);p.status='cancelled'
    for t in db.scalars(select(m.Task).where(m.Task.project_id==pid)):
        t.status='cancelled'
        for a in db.scalars(select(m.Assignment).where(m.Assignment.task_id==t.id)):
            if a.status in ACTIVE:a.status='cancelled';notify(db,a.user_id,f'Project cancelled: {p.name}')
    audit(db,u,'project.cancel',str(pid));db.commit();return {'ok':True}
def task_data(db,t):return {**public(t),'requirements':[public(r) for r in db.scalars(select(m.RequiredSkill).where(m.RequiredSkill.task_id==t.id))],'dependencies':list(db.scalars(select(m.Dependency.prerequisite_id).where(m.Dependency.task_id==t.id)))}
@app.get('/api/v1/tasks')
def tasks(project_id:int|None=None,u=Depends(user),db:DB=Depends(get_db)):
    stmt=select(m.Task).join(m.Project).where(m.Project.org_id==u.org_id)
    if project_id:project(db,u,project_id);stmt=stmt.where(m.Task.project_id==project_id)
    if u.role=='leader':stmt=stmt.where(m.Project.leader_id==u.id)
    return [task_data(db,t) for t in db.scalars(stmt)]
def validate_task(db,u,data,tid=None):
    p=project(db,u,data.project_id)
    if data.start<p.start or data.end>p.end:fail(422,'Task window must be within project dates')
    if data.hours>(data.end-data.start).total_seconds()/3600:fail(422,'Estimated hours exceed task window')
    for r in data.requirements:
        if not db.get(m.Skill,r.skill_id):fail(422,'Unknown skill')
    for dep in data.dependencies:
        d=task(db,u,dep)
        if d.id==tid or d.project_id!=p.id or d.end>data.start:fail(422,'Prerequisites must be in the same project and finish before this task')
def save_task(db,t,data):
    for k,v in data.model_dump(exclude={'requirements','dependencies'}).items():setattr(t,k,v)
    db.add(t);db.flush()
    db.execute(delete(m.RequiredSkill).where(m.RequiredSkill.task_id==t.id));db.execute(delete(m.Dependency).where(m.Dependency.task_id==t.id))
    for r in data.requirements:db.add(m.RequiredSkill(task_id=t.id,**r.model_dump()))
    for d in set(data.dependencies):db.add(m.Dependency(task_id=t.id,prerequisite_id=d))
@app.post('/api/v1/tasks',status_code=201)
def create_task(data:s.TaskIn,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');validate_task(db,u,data);t=m.Task();save_task(db,t,data);audit(db,u,'task.create',data.name);db.commit();return task_data(db,t)
@app.put('/api/v1/tasks/{tid}')
def edit_task(tid:int,data:s.TaskIn,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');t=task(db,u,tid)
    if db.scalar(select(m.Assignment.id).where(m.Assignment.task_id==tid,m.Assignment.status.in_(ACTIVE))):fail(409,'Task has active assignments. Resolve these before changing its constraints.')
    validate_task(db,u,data,tid);save_task(db,t,data);audit(db,u,'task.update',str(tid));db.commit();return task_data(db,t)
@app.delete('/api/v1/tasks/{tid}')
def cancel_task(tid:int,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');t=task(db,u,tid);t.status='cancelled'
    for a in db.scalars(select(m.Assignment).where(m.Assignment.task_id==tid,m.Assignment.status.in_(ACTIVE))):a.status='cancelled';notify(db,a.user_id,f'Task cancelled: {t.name}')
    audit(db,u,'task.cancel',str(tid));db.commit();return {'ok':True}

def snapshot(db,org_id):
    ts=list(db.scalars(select(m.Task).join(m.Project).where(m.Project.org_id==org_id,m.Project.status.in_(['active','planned']),m.Task.status.not_in(['cancelled','completed']))))
    vs=list(db.scalars(select(m.User).where(m.User.org_id==org_id,m.User.role.in_(['volunteer','leader']))))
    return {'tasks':[{**{k:(v.isoformat() if hasattr(v,'isoformat') else v) for k,v in task_data(db,t).items()},'category':db.get(m.Project,t.project_id).category} for t in ts],
        'volunteers':[{**{k:public(v)[k] for k in ['id','name','active','weekly_hours','experience','interests','learning_goals']},'skills':{str(x.skill_id):{'level':x.level,'verified':x.verified} for x in db.scalars(select(m.VolunteerSkill).where(m.VolunteerSkill.user_id==v.id))},'availability':[{'start':w.start.isoformat(),'end':w.end.isoformat()} for w in db.scalars(select(m.Availability).where(m.Availability.user_id==v.id))]} for v in vs],
        'assignments':[public(a) for a in db.scalars(select(m.Assignment).where(m.Assignment.task_id.in_([t.id for t in ts])))]}

def apply_scenario(snap,scenario):
    out=copy.deepcopy(snap)
    if not scenario:return out
    kind=scenario['kind'];uid=scenario.get('user_id');tid=scenario.get('task_id')
    if kind in {'withdrawal','unavailable'}:
        v=next((v for v in out['volunteers'] if v['id']==uid),None)
        if not v:fail(422,'Volunteer not in workspace')
        v['active']=False
    else:
        t=next((t for t in out['tasks'] if t['id']==tid),None)
        if kind=='urgent':
            urgent=scenario.get('urgent')
            if not urgent:fail(422,'Provide urgent task details')
            out['tasks'].append({**urgent,'id':-1,'category':'Community','status':'open','progress':0})
        elif not t:fail(422,'Task not in workspace')
        elif kind=='capacity':
            if not scenario.get('value') or scenario['value']<t['minimum']:fail(422,'Capacity must meet minimum staffing')
            t['capacity']=scenario['value']
        elif kind=='deadline':
            if not scenario.get('deadline') or scenario['deadline']<=t['start']:fail(422,'Deadline must follow start')
            t['end']=scenario['deadline']
        elif kind=='mandatory':
            r=next((r for r in t['requirements'] if r['skill_id']==scenario.get('value')),None)
            if not r:fail(422,'Select an existing task skill requirement')
            r['mandatory']=True
        elif kind=='cancel':
            t['capacity']=0;t['minimum']=1
            if any(a['task_id']==tid and a['status'] in ACTIVE and (a['locked'] or a['status'] in {'accepted','confirmed','in_progress','completed'}) for a in out['assignments']):fail(409,'Resolve locked assignments before cancelling in a scenario')
            out['tasks'].remove(t)
    return out
def run_job(run_id):
    with SessionLocal() as db:
        r=db.get(m.OptimizationRun,run_id);r.status='running';db.commit()
        try:
            result=optimize(apply_scenario(r.snapshot,r.scenario),r.config)
            r.result=result;r.status='completed'
        except Exception as e:
            logging.exception('Optimization failed');r.status='failed';r.error=str(e) if isinstance(e,(ValueError,HTTPException)) else 'Optimization failed; inspect server logs'
        db.commit()
@app.post('/api/v1/optimization',status_code=202)
def start_run(data:s.RunIn,bg:BackgroundTasks,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator')
    if db.scalar(select(m.OptimizationRun.id).where(m.OptimizationRun.org_id==u.org_id,m.OptimizationRun.status.in_(['queued','running']))):fail(409,'An optimization is already running for this organization')
    snap=snapshot(db,u.org_id)
    if not snap['tasks']:fail(422,'Create at least one active task first')
    scenario=data.scenario.model_dump(mode='json') if data.scenario else {}
    if scenario.get('kind')=='urgent':validate_task(db,u,data.scenario.urgent)
    apply_scenario(snap,scenario)
    r=m.OptimizationRun(org_id=u.org_id,author_id=u.id,config=data.model_dump(exclude={'scenario'}),snapshot=snap,scenario=scenario);db.add(r);db.flush();audit(db,u,'optimization.start',str(r.id));db.commit();bg.add_task(run_job,r.id);return public(r)
@app.get('/api/v1/optimization')
def runs(u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');return [public(r) for r in db.scalars(select(m.OptimizationRun).where(m.OptimizationRun.org_id==u.org_id).order_by(m.OptimizationRun.id.desc()).limit(25))]
@app.get('/api/v1/optimization/{rid}')
def get_run(rid:int,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');r=db.get(m.OptimizationRun,rid)
    if not r or r.org_id!=u.org_id:fail(404,'Run not found')
    return public(r)
@app.post('/api/v1/optimization/{rid}/publish')
def publish(rid:int,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');r=db.get(m.OptimizationRun,rid)
    if not r or r.org_id!=u.org_id:fail(404,'Run not found')
    if r.status!='completed' or r.published:fail(409,'Run is incomplete or already published')
    if snapshot(db,u.org_id)!=r.snapshot:fail(409,'Live data changed since this run. Run optimization again before publishing.')
    scenario=r.scenario or {};kind=scenario.get('kind');tid=scenario.get('task_id');idmap={}
    if kind in {'withdrawal','unavailable'}:
        target=db.get(m.User,scenario['user_id'])
        # Availability changes are explicit; account login is not deactivated.
        db.execute(delete(m.Availability).where(m.Availability.user_id==target.id))
    elif kind=='capacity':task(db,u,tid).capacity=scenario['value']
    elif kind=='deadline':
        t=task(db,u,tid);end=s.Window(start=t.start,end=scenario['deadline']).end
        if end>project(db,u,t.project_id).end:fail(422,'Deadline falls outside project window')
        t.end=end
    elif kind=='mandatory':
        req=db.scalar(select(m.RequiredSkill).where(m.RequiredSkill.task_id==tid,m.RequiredSkill.skill_id==scenario['value']));req.mandatory=True
    elif kind=='cancel':task(db,u,tid).status='cancelled'
    elif kind=='urgent':
        data=s.TaskIn(**scenario['urgent']);validate_task(db,u,data);t=m.Task();save_task(db,t,data);idmap[-1]=t.id
    desired={(idmap.get(int(tid),int(tid)),uid) for tid,team in r.result['allocation'].items() for uid in team}
    affected_task_ids=[t['id'] for t in r.snapshot['tasks']]+list(idmap.values())
    existing=list(db.scalars(select(m.Assignment).join(m.Task).join(m.Project).where(m.Project.org_id==u.org_id,m.Assignment.task_id.in_(affected_task_ids))))
    for a in existing:
        if a.status in ACTIVE and (a.task_id,a.user_id) not in desired:
            if a.locked or a.status in {'accepted','confirmed','in_progress','completed'}:fail(409,'Cannot replace a locked or confirmed assignment')
            a.status='cancelled';notify(db,a.user_id,'Your proposed assignment was updated. Please review your workspace.')
    for tid,uid in desired:
        a=next((a for a in existing if a.task_id==tid and a.user_id==uid),None)
        explanation=next((e for e in r.result['explanations'] if idmap.get(e['task_id'],e['task_id'])==tid and e['user_id']==uid),{})
        if a and a.status in ACTIVE:continue
        if not a:a=m.Assignment(task_id=tid,user_id=uid);db.add(a)
        a.status='invited';a.explanation=explanation;notify(db,uid,f'New assignment invitation: {db.get(m.Task,tid).name}')
    r.published=True;audit(db,u,'reallocation.apply' if scenario else 'assignments.publish',str(r.id));db.commit();return {'ok':True,'count':len(desired)}
@app.get('/api/v1/assignments')
def assignments(u=Depends(user),db:DB=Depends(get_db)):
    stmt=select(m.Assignment).join(m.Task).join(m.Project).where(m.Project.org_id==u.org_id)
    if u.role=='volunteer':stmt=stmt.where(m.Assignment.user_id==u.id)
    if u.role=='leader':stmt=stmt.where(m.Project.leader_id==u.id)
    return [{**public(a),'volunteer_name':db.get(m.User,a.user_id).name,'task_name':db.get(m.Task,a.task_id).name} for a in db.scalars(stmt)]
@app.post('/api/v1/assignments/{aid}/respond')
def respond(aid:int,data:s.Respond,u=Depends(user),db:DB=Depends(get_db)):
    a=assignment(db,u,aid)
    if a.user_id!=u.id:fail(403,'Only the invited volunteer can respond')
    if data.status in {'accepted','declined'} and a.status!='invited':fail(409,'Invitation has already been answered')
    if data.status=='withdrawn' and a.status not in {'invited','accepted','confirmed'}:fail(409,'Assignment cannot be withdrawn in its current state')
    a.status=data.status
    if data.status=='withdrawn':a.locked=False
    for coord in db.scalars(select(m.User).where(m.User.org_id==u.org_id,m.User.role=='coordinator')):notify(db,coord.id,f'{u.name} {data.status} {db.get(m.Task,a.task_id).name}')
    audit(db,u,'assignment.'+data.status,str(aid));db.commit();return public(a)
@app.post('/api/v1/assignments/{aid}/lock')
def lock(aid:int,data:dict,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');a=assignment(db,u,aid)
    if a.status not in ACTIVE:fail(409,'Only active assignments can be locked')
    a.locked=bool(data.get('locked',True));audit(db,u,'assignment.lock',str(aid));db.commit();return public(a)
@app.post('/api/v1/tasks/{tid}/progress')
def progress(tid:int,data:s.ProgressIn,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator','leader');t=task(db,u,tid)
    if t.status=='cancelled':fail(409,'Task is cancelled')
    dependencies=list(db.scalars(select(m.Dependency).where(m.Dependency.task_id==tid)))
    if data.percent>0 and any(db.get(m.Task,d.prerequisite_id).progress<100 for d in dependencies):fail(409,'Complete prerequisites first')
    t.progress=data.percent;t.status='completed' if data.percent==100 else 'in_progress'
    db.add(m.Progress(task_id=tid,author_id=u.id,percent=data.percent,note=data.note))
    for a in db.scalars(select(m.Assignment).where(m.Assignment.task_id==tid,m.Assignment.status.in_(['accepted','confirmed','in_progress']))):
        a.status='completed' if data.percent==100 else 'in_progress'
        if data.percent==100:notify(db,a.user_id,f'Task completed: {t.name}')
    audit(db,u,'task.progress',f'{tid}: {data.percent}%');db.commit();return task_data(db,t)
@app.post('/api/v1/applications',status_code=201)
def apply(data:dict,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'volunteer','leader');pid=data.get('project_id');p=project(db,u,pid)
    if p.status not in {'active','planned'}:fail(409,'Project is not accepting applications')
    if db.scalar(select(m.Application).where(m.Application.project_id==pid,m.Application.user_id==u.id)):fail(409,'You have already applied')
    a=m.Application(project_id=pid,user_id=u.id);db.add(a);audit(db,u,'application.create',str(pid));db.commit();return public(a)
@app.get('/api/v1/applications')
def applications(u=Depends(user),db:DB=Depends(get_db)):
    stmt=select(m.Application).join(m.Project).where(m.Project.org_id==u.org_id)
    if u.role not in {'admin','coordinator'}:stmt=stmt.where(m.Application.user_id==u.id)
    return [public(a) for a in db.scalars(stmt)]
@app.post('/api/v1/replacements',status_code=201)
def replacement(data:dict,u=Depends(user),db:DB=Depends(get_db)):
    a=assignment(db,u,data.get('assignment_id'));reason=str(data.get('reason','')).strip()
    if not 3<=len(reason)<=2000:fail(422,'Please describe the replacement reason')
    r=m.ReplacementRequest(assignment_id=a.id,author_id=u.id,reason=reason);db.add(r)
    for c in db.scalars(select(m.User).where(m.User.org_id==u.org_id,m.User.role=='coordinator')):notify(db,c.id,f'Replacement requested for {db.get(m.Task,a.task_id).name}: {reason}')
    audit(db,u,'replacement.request',str(a.id));db.commit();return public(r)
@app.get('/api/v1/notifications')
def notifications(u=Depends(user),db:DB=Depends(get_db)):return [public(n) for n in db.scalars(select(m.Notification).where(m.Notification.user_id==u.id).order_by(m.Notification.id.desc()).limit(100))]
@app.post('/api/v1/notifications/read')
def read_notifications(u=Depends(user),db:DB=Depends(get_db)):
    for n in db.scalars(select(m.Notification).where(m.Notification.user_id==u.id)):n.read=True
    db.commit();return {'ok':True}
@app.get('/api/v1/hours')
def hours(u=Depends(user),db:DB=Depends(get_db)):
    stmt=select(m.HourRecord).join(m.Assignment).join(m.Task).join(m.Project).where(m.Project.org_id==u.org_id)
    if u.role=='volunteer':stmt=stmt.where(m.Assignment.user_id==u.id)
    if u.role=='leader':stmt=stmt.where(m.Project.leader_id==u.id)
    return [public(h) for h in db.scalars(stmt)]
@app.post('/api/v1/hours',status_code=201)
def record_hours(data:s.HoursIn,u=Depends(user),db:DB=Depends(get_db)):
    a=assignment(db,u,data.assignment_id)
    if a.status not in {'accepted','confirmed','in_progress','completed'}:fail(409,'Hours require an accepted assignment')
    if db.scalar(select(m.HourRecord).where(m.HourRecord.assignment_id==a.id)):fail(409,'Hours already submitted')
    h=m.HourRecord(**data.model_dump());db.add(h);audit(db,u,'hours.submit',str(a.id));db.commit();return public(h)
@app.post('/api/v1/hours/{hid}/approve')
def approve_hours(hid:int,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');h=db.get(m.HourRecord,hid)
    if not h:fail(404,'Hour record not found')
    a=assignment(db,u,h.assignment_id)
    if a.user_id==u.id:fail(403,'You cannot approve your own hours')
    h.approved=True
    if not db.scalar(select(m.Achievement).where(m.Achievement.user_id==a.user_id,m.Achievement.name=='First verified contribution')):db.add(m.Achievement(user_id=a.user_id,name='First verified contribution'))
    audit(db,u,'hours.approve',str(hid));db.commit();return public(h)
@app.post('/api/v1/attendance')
def attendance(data:dict,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator','leader');a=assignment(db,u,data.get('assignment_id'))
    if a.status not in {'accepted','confirmed','in_progress','completed'}:fail(409,'Attendance requires an accepted assignment')
    item=db.scalar(select(m.Attendance).where(m.Attendance.assignment_id==a.id))
    if not item:item=m.Attendance(assignment_id=a.id,recorded_by=u.id);db.add(item)
    item.present=bool(data.get('present'));item.recorded_by=u.id;audit(db,u,'attendance.record',str(a.id));db.commit();return public(item)
@app.get('/api/v1/attendance')
def get_attendance(u=Depends(user),db:DB=Depends(get_db)):
    stmt=select(m.Attendance).join(m.Assignment).join(m.Task).join(m.Project).where(m.Project.org_id==u.org_id)
    if u.role=='volunteer':stmt=stmt.where(m.Assignment.user_id==u.id)
    if u.role=='leader':stmt=stmt.where(m.Project.leader_id==u.id)
    return [public(a) for a in db.scalars(stmt)]
@app.get('/api/v1/feedback')
def feedback(u=Depends(user),db:DB=Depends(get_db)):
    stmt=select(m.Feedback).join(m.Project).where(m.Project.org_id==u.org_id)
    if u.role not in {'admin','coordinator'}:stmt=stmt.where(m.Feedback.author_id==u.id)
    return [public(f) for f in db.scalars(stmt)]
@app.post('/api/v1/feedback',status_code=201)
def add_feedback(data:s.FeedbackIn,u=Depends(user),db:DB=Depends(get_db)):
    project(db,u,data.project_id)
    if u.role=='volunteer' and not db.scalar(select(m.Assignment.id).join(m.Task).where(m.Task.project_id==data.project_id,m.Assignment.user_id==u.id)):fail(403,'Feedback requires project participation')
    f=m.Feedback(author_id=u.id,**data.model_dump());db.add(f);db.commit();return public(f)
@app.get('/api/v1/achievements')
def achievements(u=Depends(user),db:DB=Depends(get_db)):return [public(x) for x in db.scalars(select(m.Achievement).where(m.Achievement.user_id==u.id))]
@app.get('/api/v1/analytics')
def analytics(u=Depends(user),db:DB=Depends(get_db)):
    ps=projects(u=u,db=db);ts=tasks(u=u,db=db);aa=assignments(u=u,db=db);hh=hours(u=u,db=db)
    users=db.scalar(select(func.count()).select_from(m.User).where(m.User.org_id==u.org_id,m.User.active==True)) if u.role in {'admin','coordinator'} else len({a['user_id'] for a in aa})
    active=[a for a in aa if a['status'] in ACTIVE]
    return {'projects':len([p for p in ps if p['status']=='active']),'volunteers':users,'tasks':len(ts),'completed_tasks':sum(t['progress']==100 for t in ts),'hours':sum(h['hours'] for h in hh if h['approved']),'assignments':len(active),'acceptance_rate':sum(a['status'] in {'accepted','confirmed','in_progress','completed'} for a in aa)/max(1,len([a for a in aa if a['status']!='cancelled'])),'unfilled':sum(max(0,t['minimum']-sum(a['task_id']==t['id'] for a in active)) for t in ts if t['status']!='cancelled'),'progress':[{'name':p['name'],'progress':round(sum(t['progress'] for t in ts if t['project_id']==p['id'])/max(1,sum(t['project_id']==p['id'] for t in ts)))} for p in ps]}
@app.get('/api/v1/audit')
def logs(u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');return [public(x) for x in db.scalars(select(m.AuditLog).where(m.AuditLog.org_id==u.org_id).order_by(m.AuditLog.id.desc()).limit(200))]
@app.get('/api/v1/admin/users')
def admin_users(u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin');return [public(v) for v in db.scalars(select(m.User).order_by(m.User.id))]
@app.put('/api/v1/admin/users/{uid}')
def edit_user(uid:int,data:s.UserUpdate,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin');v=db.get(m.User,uid)
    if not v:fail(404,'User not found')
    if v.id==u.id and (not data.active or data.role!='admin'):fail(409,'You cannot remove your own administrator access')
    if v.role=='admin' and (not data.active or data.role!='admin') and db.scalar(select(func.count()).select_from(m.User).where(m.User.role=='admin',m.User.active==True))<=1:fail(409,'Preserve at least one active administrator')
    v.role=data.role;v.active=data.active
    if not data.active:db.execute(delete(m.Session).where(m.Session.user_id==uid))
    audit(db,u,'user.update',f'{uid}: {data.role}, active={data.active}');db.commit();return public(v)
@app.get('/api/v1/admin/organizations')
def admin_orgs(u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin');return [public(o) for o in db.scalars(select(m.Organization))]
def safe_cell(value):
    value=str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value
@app.get('/api/v1/reports/{kind}.csv')
def export(kind:str,u=Depends(user),db:DB=Depends(get_db)):
    if kind=='assignments':rows=assignments(u=u,db=db)
    elif kind=='hours':rows=hours(u=u,db=db)
    elif kind=='tasks':rows=tasks(u=u,db=db)
    elif kind=='volunteers':rows=volunteers(u=u,db=db)
    else:fail(404,'Unknown report')
    output=io.StringIO();fields=list(rows[0]) if rows else ['id'];writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for row in rows:writer.writerow({k:safe_cell(v) for k,v in row.items()})
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="skillweave-{kind}.csv"'})
@app.post('/api/v1/import/tasks')
async def import_tasks(file:UploadFile,u=Depends(user),db:DB=Depends(get_db)):
    roles(u,'admin','coordinator');raw=await file.read(1_000_001)
    if len(raw)>1_000_000:fail(413,'CSV must be smaller than 1 MB')
    try:rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    except (UnicodeDecodeError,csv.Error):fail(422,'Upload a UTF-8 CSV file')
    if len(rows)>500:fail(422,'Maximum 500 rows')
    errors=[];valid=[]
    for i,row in enumerate(rows,2):
        try:
            data=s.TaskIn(**row);validate_task(db,u,data);valid.append(data)
        except (ValueError,HTTPException) as e:errors.append({'row':i,'error':str(e)})
    if errors:return {'imported':0,'errors':errors}
    for data in valid:save_task(db,m.Task(),data)
    audit(db,u,'tasks.import',str(len(valid)));db.commit();return {'imported':len(valid),'errors':[]}
