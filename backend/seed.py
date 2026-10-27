"""Non-destructive, repeatable fictional demonstration fixture."""
from datetime import datetime, timedelta
import os
from sqlalchemy import select
from argon2 import PasswordHasher
from .database import SessionLocal
from . import models as m

def seed(include_history=True):
    with SessionLocal() as db:
        coordinator=db.scalar(select(m.User).where(m.User.email=='coordinator@demo.skillweave.test'))
        if coordinator:
            added=seed_history(db,coordinator.org_id) if include_history else False
            db.commit()
            print('Demo history added; existing data preserved.' if added else 'Demo already seeded; existing data preserved.');return
        org=m.Organization(name='Together Foundation',description='Fictional community organization · development demo');db.add(org);db.flush()
        password=os.getenv('DEMO_PASSWORD','WeaveDemo!2026');ph=PasswordHasher()
        people=[('admin','Alex Morgan'),('coordinator','Sam Rivera'),('leader','Jordan Lee'),('leader2','Taylor Quinn'),('volunteer','Avery Patel'),('volunteer2','Jamie Chen'),('volunteer3','Morgan Blake'),('volunteer4','Riley Shaw'),('volunteer5','Casey Ellis'),('volunteer6','Drew Park'),('volunteer7','Skyler Reed'),('volunteer8','Robin Lane')]
        users=[]
        base=datetime(2026,11,2,9)
        for i,(handle,name) in enumerate(people):
            role='leader' if handle.startswith('leader') else 'volunteer' if handle.startswith('volunteer') else handle
            u=m.User(email=f'{handle}@demo.skillweave.test',name=name,role=role,org_id=org.id,password_hash=ph.hash(password),weekly_hours=4+(i%4)*4,experience=i%6,interests=['Environment','Education'] if i%2 else ['Health','Community'],learning_goals=['2','3'])
            db.add(u);db.flush();db.add(m.Membership(user_id=u.id,org_id=org.id));users.append(u)
            if role in {'leader','volunteer'}:
                for day in range(6):db.add(m.Availability(user_id=u.id,start=base+timedelta(days=day),end=base+timedelta(days=day,hours=8)))
            db.add(m.Notification(user_id=u.id,text='Welcome to the SkillWeave fictional demo. Your workspace is ready.'))
        names=['Community outreach','Teaching','Event planning','First aid','Design','Data analysis','Environmental care','Sign language']
        skills=[]
        for name in names:
            x=db.scalar(select(m.Skill).where(m.Skill.name==name))
            if not x:x=m.Skill(name=name);db.add(x);db.flush()
            skills.append(x)
        for i,u in enumerate(users[2:]):
            for j in range(3):
                sk=skills[(i+j)%7];db.add(m.VolunteerSkill(user_id=u.id,skill_id=sk.id,level=2+(i+j)%4,verified=(i+j)%3==0))
        projects=[('Green neighborhood','Environment','Riverside Park','A greener block, one shared effort at a time.'),('Learning together','Education','Community Library','Help young learners build confidence and curiosity.'),('Community care day','Health','North Community Hall','A day of practical support and community connection.'),('Accessible futures','Community','Remote','Make community information more accessible to everyone.')]
        for i,(name,cat,loc,desc) in enumerate(projects):
            p=m.Project(org_id=org.id,name=name,category=cat,location=loc,description=desc,start=base,end=base+timedelta(days=6),leader_id=users[2+i%2].id)
            db.add(p);db.flush()
            for j in range(2):
                t=m.Task(project_id=p.id,name=[['Park restoration','Volunteer welcome desk'],['Reading circle','Learning materials'],['Care station','Community outreach'],['Accessible information','Inclusive workshop']][i][j],description='Fictional demo task. Review requirements before publishing invitations.',start=base+timedelta(days=i,hours=j),end=base+timedelta(days=i,hours=j+3),hours=3,capacity=3,minimum=2,priority=5 if j==0 else 3,difficulty=3)
                db.add(t);db.flush()
                sk=skills[7] if i==3 and j==0 else skills[(i*2+j)%7]
                db.add(m.RequiredSkill(task_id=t.id,skill_id=sk.id,level=3,mandatory=i==3 and j==0,verified=False))
        db.add(m.AuditLog(org_id=org.id,actor_id=users[0].id,action='demo.seed',detail='Fictional data only; no measured real-world impact.'))
        if include_history:seed_history(db,org.id)
        db.commit();print('Demo seeded. Login handles: admin, coordinator, leader, leader2, volunteer through volunteer8 @demo.skillweave.test. Password: '+password)

def seed_history(db,org_id):
    """Add a versioned, fictional history once, without resetting live or edited records."""
    marker='demo.history.v1'
    if db.scalar(select(m.AuditLog.id).where(m.AuditLog.org_id==org_id,m.AuditLog.action==marker)):return False
    def demo(handle):
        u=db.scalar(select(m.User).where(m.User.email==handle+'@demo.skillweave.test',m.User.org_id==org_id))
        if not u:raise ValueError('History needs the original demo accounts in the same organization; existing data was not reset.')
        return u
    coordinator=demo('coordinator');leaders=[demo('leader'),demo('leader2')]
    volunteers=[demo('volunteer' if i==0 else f'volunteer{i+1}') for i in range(8)]
    catalog={s.name:s.id for s in db.scalars(select(m.Skill))}
    plans=[
        ('Riverbank renewal','Environment','Riverside Trail',datetime(2026,9,5,9),['Trail clean-up','Waste sorting workshop'],'Environmental care'),
        ('Back-to-school bridge','Education','East Community Library',datetime(2026,9,12,9),['Reading buddies','Learning kit assembly'],'Teaching'),
        ('Neighborhood wellness weekend','Health','North Community Hall',datetime(2026,9,19,9),['Wellness welcome desk','Health information outreach'],'Community outreach'),
        ('Community harvest festival','Community','Central Community Garden',datetime(2026,10,3,9),['Festival setup','Community welcome team'],'Event planning'),
    ]
    reserved=[p[0] for p in plans]+['Digital confidence week']
    if db.scalar(select(m.Project.id).where(m.Project.org_id==org_id,m.Project.name.in_(reserved))):
        raise ValueError('A history project name already exists without its seed marker. Resolve the name conflict; no records were overwritten.')
    for i,(name,category,location,start,names,skill) in enumerate(plans):
        leader=leaders[i%2]
        p=m.Project(org_id=org_id,name=name,description='Fictional completed demo project. Volunteers worked together on '+name.lower()+'.',category=category,location=location,start=start,end=start+timedelta(days=1,hours=4),status='completed',leader_id=leader.id)
        db.add(p);db.flush()
        for j,title in enumerate(names):
            begin=start+timedelta(days=j)
            t=m.Task(project_id=p.id,name=title,description='Fictional historical contribution for demonstration.',start=begin,end=begin+timedelta(hours=3),hours=3,capacity=4,minimum=2,priority=3,difficulty=2,status='completed',progress=100)
            db.add(t);db.flush();db.add(m.RequiredSkill(task_id=t.id,skill_id=catalog[skill],level=2,mandatory=False))
            db.add(m.Progress(task_id=t.id,author_id=leader.id,percent=50,note='Demo history: team checked in and work underway.',created_at=begin+timedelta(hours=1)))
            db.add(m.Progress(task_id=t.id,author_id=leader.id,percent=100,note='Demo history: planned responsibilities completed and reviewed.',created_at=begin+timedelta(hours=3)))
            roster=volunteers[j*4:j*4+4]
            for v in roster:
                a=m.Assignment(task_id=t.id,user_id=v.id,status='completed',locked=True,explanation={'source':'fictional_demo_history','reason':'Historical sample participation; not an algorithm recommendation.'})
                db.add(a);db.flush()
                db.add(m.Attendance(assignment_id=a.id,present=True,recorded_by=leader.id))
                db.add(m.HourRecord(assignment_id=a.id,hours=3,approved=True))
                db.add(m.Application(project_id=p.id,user_id=v.id,status='accepted'))
                db.add(m.Feedback(project_id=p.id,author_id=v.id,rating=4+(v.id+i)%2,text=['Clear responsibilities and a welcoming team made it easy to contribute.','I enjoyed working with the team and would appreciate an earlier briefing next time.','A useful chance to practice my skills while supporting the community.','The team leader was supportive and the schedule respected my availability.'][(v.id+i)%4]+' (Fictional demo feedback.)',private=True))
                db.add(m.Notification(user_id=v.id,text=f'Demo history: your 3 hours for {title} were approved.',read=True,created_at=begin+timedelta(hours=4)))
        db.add(m.Feedback(project_id=p.id,author_id=leader.id,rating=5,text='Demo completion report: both task groups completed their responsibilities; attendance and hours reviewed.',private=True))
        db.add(m.AuditLog(org_id=org_id,actor_id=coordinator.id,action='demo.project.completed',detail=f'Fictional project: {name}; 24 approved volunteer hours.',created_at=p.end))
    # A current project makes progress, pending review, and invitation queues useful too.
    start=datetime(2026,10,24,9)
    p=m.Project(org_id=org_id,name='Digital confidence week',description='Fictional ongoing demo: help residents build confidence using everyday digital tools.',category='Education',location='Community Learning Hub',start=start,end=datetime(2026,10,30,17),status='active',leader_id=leaders[0].id)
    db.add(p);db.flush()
    for j,(title,status,percent,day) in enumerate([('Device setup clinic','completed',100,0),('Digital skills practice','in_progress',50,1),('Online safety workshop','open',0,3)]):
        begin=start+timedelta(days=day)
        t=m.Task(project_id=p.id,name=title,description='Fictional ongoing demo task.',start=begin,end=begin+timedelta(hours=2),hours=2,capacity=4,minimum=2,priority=4,difficulty=2,status=status,progress=percent)
        db.add(t);db.flush();db.add(m.RequiredSkill(task_id=t.id,skill_id=catalog['Teaching'],level=2,mandatory=False))
        if percent:db.add(m.Progress(task_id=t.id,author_id=leaders[0].id,percent=percent,note='Demo team update: session delivered.' if percent==100 else 'Demo team update: guided practice is underway.',created_at=begin+timedelta(hours=1)))
        for v in volunteers+leaders:
            db.add(m.Availability(user_id=v.id,start=begin,end=begin+timedelta(hours=4)))
        roster=volunteers[:4] if j in {0,2} else volunteers[4:]
        for k,v in enumerate(roster):
            state='completed' if j==0 else ('in_progress' if k<2 else 'accepted') if j==1 else ['invited','invited','declined','withdrawn'][k]
            a=m.Assignment(task_id=t.id,user_id=v.id,status=state,locked=state in {'completed','in_progress'},explanation={'source':'fictional_demo_history','reason':'Sample current project participation; not a computed match.'})
            db.add(a);db.flush()
            if j<2:db.add(m.Attendance(assignment_id=a.id,present=True,recorded_by=leaders[0].id))
            if j==0:db.add(m.HourRecord(assignment_id=a.id,hours=2,approved=k!=3))
            db.add(m.Notification(user_id=v.id,text=f'Demo project update: {title} — {state.replace("_"," ")}.',read=j==0,created_at=begin))
            if state=='withdrawn':db.add(m.ReplacementRequest(assignment_id=a.id,author_id=leaders[0].id,reason='Fictional demo: volunteer withdrew because of a schedule change; coordinator review requested.'))
    for v in volunteers:
        for name in ['First verified contribution','Four community projects completed']:
            if not db.scalar(select(m.Achievement.id).where(m.Achievement.user_id==v.id,m.Achievement.name==name)):db.add(m.Achievement(user_id=v.id,name=name))
    db.add(m.Notification(user_id=coordinator.id,text='Demo history is ready: completed projects, approved hours, one pending hours review, and a replacement request.',read=False))
    for leader in leaders:db.add(m.Notification(user_id=leader.id,text='Demo history: your assigned projects include completed teams, attendance, and completion feedback.',read=False))
    db.add(m.AuditLog(org_id=org_id,actor_id=coordinator.id,action=marker,detail='Added fictional project and contribution history v1. Existing records preserved.'))
    db.flush()
    return True
if __name__=='__main__':seed()
