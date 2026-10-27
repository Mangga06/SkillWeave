import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.database import Base, get_db
from backend.main import app
from backend import main,seed

@pytest.fixture
def database():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(engine,expire_on_commit=False)
    main.SessionLocal=factory;seed.SessionLocal=factory;seed.seed(include_history=False)
    def override():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=override
    yield factory
    app.dependency_overrides.clear();engine.dispose()
@pytest.fixture
def client(database):
    main.attempts.clear()
    with TestClient(app,headers={'X-Requested-With':'SkillWeave'}) as c:yield c
@pytest.fixture
def coordinator(client):
    assert client.post('/api/v1/auth/login',json={'email':'coordinator@demo.skillweave.test','password':'WeaveDemo!2026'}).status_code==200
    return client
