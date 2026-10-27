from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1,max_length=128)
    @field_validator('email')
    @classmethod
    def email_format(cls,v):
        if '@' not in v or '.' not in v.split('@')[-1]: raise ValueError('Enter a valid email')
        return v.strip().lower()
class Register(Login):
    name: str = Field(min_length=2,max_length=100)
    password: str = Field(min_length=10,max_length=128)
    invite_token: str = Field(default='',max_length=200)
class InviteIn(Login):
    password: str = 'invite'
    role: Literal['volunteer','leader'] = 'volunteer'
class SkillEntry(BaseModel):
    skill_id: int
    level: int = Field(ge=1,le=5)
class Window(BaseModel):
    start: datetime
    end: datetime
    @model_validator(mode='after')
    def dates(self):
        self.start=self.start.replace(tzinfo=None); self.end=self.end.replace(tzinfo=None)
        if self.end <= self.start: raise ValueError('End must follow start')
        return self
class Profile(BaseModel):
    name: str = Field(min_length=2,max_length=100)
    weekly_hours: float = Field(ge=0,le=168)
    experience: float = Field(ge=0,le=60)
    interests: list[str] = Field(max_length=20)
    learning_goals: list[str] = Field(max_length=20)
    notifications_enabled: bool = True
    skills: list[SkillEntry] = Field(max_length=100)
    availability: list[Window] = Field(max_length=200)
class ProjectIn(Window):
    name: str = Field(min_length=3,max_length=150)
    description: str = Field(default='',max_length=5000)
    category: str = Field(default='Community',max_length=80)
    location: str = Field(default='Remote',max_length=200)
    status: Literal['active','planned','completed','cancelled'] = 'active'
    leader_id: int | None = None
class Requirement(SkillEntry):
    mandatory: bool = False
    verified: bool = False
class TaskIn(Window):
    project_id: int
    name: str = Field(min_length=3,max_length=150)
    description: str = Field(default='',max_length=5000)
    hours: float = Field(gt=0,le=168)
    capacity: int = Field(ge=1,le=100)
    minimum: int = Field(ge=1,le=100)
    priority: int = Field(ge=1,le=5)
    difficulty: int = Field(default=3,ge=1,le=5)
    requirements: list[Requirement] = Field(default_factory=list,max_length=50)
    dependencies: list[int] = Field(default_factory=list,max_length=50)
    @model_validator(mode='after')
    def sizes(self):
        if self.minimum > self.capacity: raise ValueError('Minimum staffing exceeds capacity')
        if len({r.skill_id for r in self.requirements})!=len(self.requirements): raise ValueError('Duplicate required skill')
        return self
class Scenario(BaseModel):
    kind: Literal['withdrawal','unavailable','capacity','deadline','mandatory','cancel','urgent']
    user_id: int | None = None
    task_id: int | None = None
    value: int | None = None
    deadline: datetime | None = None
    urgent: TaskIn | None = None
class RunIn(BaseModel):
    generations: int = Field(default=40,ge=2,le=150)
    population: int = Field(default=30,ge=6,le=80)
    mutation: float = Field(default=.25,ge=0,le=1)
    seed: int = 42
    weights: dict[str,float] | None = None
    scenario: Scenario | None = None
    @field_validator('weights')
    @classmethod
    def weights_valid(cls,v):
        from .optimizer import DEFAULT_WEIGHTS
        if v is not None and (set(v)!=set(DEFAULT_WEIGHTS) or any(not 0<=n<=1 for n in v.values()) or sum(v.values())<=0): raise ValueError('Supply all seven weights between 0 and 1 with positive total')
        return v
class Respond(BaseModel):
    status: Literal['accepted','declined','withdrawn']
class ProgressIn(BaseModel):
    percent: int = Field(ge=0,le=100)
    note: str = Field(default='',max_length=2000)
class HoursIn(BaseModel):
    assignment_id: int
    hours: float = Field(gt=0,le=168)
class FeedbackIn(BaseModel):
    project_id: int
    rating: int = Field(ge=1,le=5)
    text: str = Field(min_length=3,max_length=4000)
    private: bool = True
class UserUpdate(BaseModel):
    role: Literal['admin','coordinator','leader','volunteer']
    active: bool
