from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint
from .database import Base, now

class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    description = Column(String, default='')
    active = Column(Boolean, default=True)
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(254), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default='volunteer')
    org_id = Column(ForeignKey('organizations.id'), nullable=False, index=True)
    active = Column(Boolean, default=True)
    weekly_hours = Column(Float, default=12)
    experience = Column(Float, default=0)
    interests = Column(JSON, default=list)
    learning_goals = Column(JSON, default=list)
    notifications_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
    __table_args__ = (CheckConstraint("role IN ('admin','coordinator','leader','volunteer')"), CheckConstraint('weekly_hours >= 0'))
class Membership(Base):
    __tablename__ = 'organization_memberships'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id'), unique=True, nullable=False)
    org_id = Column(ForeignKey('organizations.id'), nullable=False)
class OrganizationInvitation(Base):
    __tablename__ = 'organization_invitations'
    id = Column(Integer, primary_key=True)
    org_id = Column(ForeignKey('organizations.id'), nullable=False)
    email = Column(String(254), nullable=False)
    role = Column(String, nullable=False, default='volunteer')
    token_hash = Column(String, unique=True, nullable=False)
    expires = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
class Session(Base):
    __tablename__ = 'sessions'
    token_hash = Column(String, primary_key=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    expires = Column(DateTime, nullable=False)
class ResetToken(Base):
    __tablename__ = 'password_reset_tokens'
    token_hash = Column(String, primary_key=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    expires = Column(DateTime, nullable=False)
class Skill(Base):
    __tablename__ = 'skills'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    category = Column(String, default='Community')
class VolunteerSkill(Base):
    __tablename__ = 'volunteer_skills'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    skill_id = Column(ForeignKey('skills.id'), nullable=False)
    level = Column(Integer, nullable=False)
    verified = Column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('user_id','skill_id'), CheckConstraint('level BETWEEN 1 AND 5'))
class Availability(Base):
    __tablename__ = 'volunteer_availability'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    __table_args__ = (CheckConstraint('end > start'),)
class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    org_id = Column(ForeignKey('organizations.id'), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(String, default='')
    category = Column(String, default='Community')
    location = Column(String, default='Remote')
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    status = Column(String, default='active')
    leader_id = Column(ForeignKey('users.id'), nullable=True)
    __table_args__ = (CheckConstraint('end > start'),)
class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    project_id = Column(ForeignKey('projects.id'), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(String, default='')
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    hours = Column(Float, default=2)
    capacity = Column(Integer, default=2)
    minimum = Column(Integer, default=1)
    priority = Column(Integer, default=3)
    difficulty = Column(Integer, default=3)
    status = Column(String, default='open')
    progress = Column(Integer, default=0)
    __table_args__ = (CheckConstraint('end > start'), CheckConstraint('capacity >= minimum AND minimum >= 1'), CheckConstraint('hours > 0'), CheckConstraint('priority BETWEEN 1 AND 5'), CheckConstraint('progress BETWEEN 0 AND 100'))
class RequiredSkill(Base):
    __tablename__ = 'task_required_skills'
    id = Column(Integer, primary_key=True)
    task_id = Column(ForeignKey('tasks.id'), nullable=False)
    skill_id = Column(ForeignKey('skills.id'), nullable=False)
    level = Column(Integer, default=2)
    mandatory = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('task_id','skill_id'), CheckConstraint('level BETWEEN 1 AND 5'))
class Dependency(Base):
    __tablename__ = 'task_dependencies'
    id = Column(Integer, primary_key=True)
    task_id = Column(ForeignKey('tasks.id'), nullable=False)
    prerequisite_id = Column(ForeignKey('tasks.id'), nullable=False)
    __table_args__ = (UniqueConstraint('task_id','prerequisite_id'), CheckConstraint('task_id != prerequisite_id'))
class Application(Base):
    __tablename__ = 'applications'
    id = Column(Integer, primary_key=True)
    project_id = Column(ForeignKey('projects.id'), nullable=False)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    status = Column(String, default='pending')
    __table_args__ = (UniqueConstraint('project_id','user_id'),)
class Assignment(Base):
    __tablename__ = 'assignments'
    id = Column(Integer, primary_key=True)
    task_id = Column(ForeignKey('tasks.id'), nullable=False, index=True)
    user_id = Column(ForeignKey('users.id'), nullable=False, index=True)
    status = Column(String, default='invited')
    locked = Column(Boolean, default=False)
    explanation = Column(JSON, default=dict)
    __table_args__ = (UniqueConstraint('task_id','user_id'),)
class Progress(Base):
    __tablename__ = 'task_progress'
    id = Column(Integer, primary_key=True)
    task_id = Column(ForeignKey('tasks.id'), nullable=False)
    author_id = Column(ForeignKey('users.id'), nullable=False)
    percent = Column(Integer, nullable=False)
    note = Column(String, default='')
    created_at = Column(DateTime, default=now)
class Attendance(Base):
    __tablename__ = 'attendance'
    id = Column(Integer, primary_key=True)
    assignment_id = Column(ForeignKey('assignments.id'), nullable=False, unique=True)
    present = Column(Boolean, default=True)
    recorded_by = Column(ForeignKey('users.id'), nullable=False)
class HourRecord(Base):
    __tablename__ = 'volunteer_hour_records'
    id = Column(Integer, primary_key=True)
    assignment_id = Column(ForeignKey('assignments.id'), nullable=False, unique=True)
    hours = Column(Float, nullable=False)
    approved = Column(Boolean, default=False)
    __table_args__ = (CheckConstraint('hours > 0 AND hours <= 168'),)
class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    project_id = Column(ForeignKey('projects.id'), nullable=False)
    author_id = Column(ForeignKey('users.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    private = Column(Boolean, default=True)
    __table_args__ = (CheckConstraint('rating BETWEEN 1 AND 5'),)
class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id'), nullable=False, index=True)
    text = Column(String, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)
class ReplacementRequest(Base):
    __tablename__ = 'replacement_requests'
    id = Column(Integer, primary_key=True)
    assignment_id = Column(ForeignKey('assignments.id'), nullable=False)
    author_id = Column(ForeignKey('users.id'), nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default='pending')
class Achievement(Base):
    __tablename__ = 'achievements'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint('user_id','name'),)
class OptimizationRun(Base):
    __tablename__ = 'optimization_runs'
    id = Column(Integer, primary_key=True)
    org_id = Column(ForeignKey('organizations.id'), nullable=False, index=True)
    author_id = Column(ForeignKey('users.id'), nullable=False)
    status = Column(String, default='queued')
    config = Column(JSON, nullable=False)
    snapshot = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    error = Column(String, nullable=True)
    scenario = Column(JSON, default=dict)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    org_id = Column(ForeignKey('organizations.id'), nullable=False, index=True)
    actor_id = Column(ForeignKey('users.id'), nullable=False)
    action = Column(String, nullable=False)
    detail = Column(String, default='')
    created_at = Column(DateTime, default=now)
