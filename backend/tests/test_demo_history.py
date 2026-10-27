from sqlalchemy import select, func
from backend import models as m, seed
from backend.database import Base
from backend.main import snapshot
from backend.optimizer import optimize

def test_history_is_complete_repeatable_and_preserves_existing(database):
    with database() as db:
        original=db.get(m.Project,1);original.description='Keep my edited project';db.commit()
    seed.seed()
    with database() as db:
        counts={table.name:db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}
        assert counts['projects']==9
        assert counts['tasks']==19
        assert counts['assignments']==44
        assert db.scalar(select(func.sum(m.HourRecord.hours)).where(m.HourRecord.approved==True))==102
        assert db.scalar(select(func.count()).select_from(m.HourRecord).where(m.HourRecord.approved==False))==1
        assert db.get(m.Project,1).description=='Keep my edited project'
        completed=list(db.scalars(select(m.Task).where(m.Task.status=='completed')))
        assert len(completed)==9
        assert all(t.progress==100 for t in completed)
        for a in db.scalars(select(m.Assignment).where(m.Assignment.status=='completed')):
            assert db.scalar(select(m.Attendance).where(m.Attendance.assignment_id==a.id)).present
            assert db.scalar(select(m.HourRecord).where(m.HourRecord.assignment_id==a.id))
        for v in db.scalars(select(m.User).where(m.User.role=='volunteer')):
            assert db.scalar(select(func.count()).select_from(m.Assignment).where(m.Assignment.user_id==v.id,m.Assignment.status=='completed'))>=4
    seed.seed()
    with database() as db:
        assert counts=={table.name:db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}

def test_history_is_visible_through_scoped_workspaces(coordinator):
    seed.seed();c=coordinator
    stats=c.get('/api/v1/analytics').json()
    assert stats['hours']==102 and stats['completed_tasks']==9
    assert stats['projects']==5
    volunteer=next(v for v in c.get('/api/v1/volunteers').json() if v['email']=='volunteer@demo.skillweave.test')
    assert len(volunteer['work_history'])==5
    assert sum(p['approved_hours'] for p in volunteer['work_history'])==14
    assert c.post('/api/v1/auth/login',json={'email':'volunteer@demo.skillweave.test','password':'WeaveDemo!2026'}).status_code==200
    assert len(c.get('/api/v1/me').json()['work_history'])==5
    assert len(c.get('/api/v1/achievements').json())==2
    assert len(c.get('/api/v1/feedback').json())==4
    assert c.post('/api/v1/auth/login',json={'email':'leader@demo.skillweave.test','password':'WeaveDemo!2026'}).status_code==200
    for v in c.get('/api/v1/volunteers').json():
        assert all(p['name'] not in {'Back-to-school bridge','Community harvest festival'} for p in v['work_history'])

def test_current_history_remains_optimizable(database):
    seed.seed()
    with database() as db:s=snapshot(db,1)
    result=optimize(s,{'population':8,'generations':3,'seed':42})
    assert result['constraint_violations']==0
    for a in s['assignments']:
        if a['status'] in {'accepted','in_progress'}:
            assert a['user_id'] in result['allocation'][a['task_id']]
