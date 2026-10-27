"""Initial normalized SkillWeave schema."""
from alembic import op
from backend.database import Base
from backend import models
revision='0001'
down_revision=None
def upgrade():Base.metadata.create_all(bind=op.get_bind())
def downgrade():Base.metadata.drop_all(bind=op.get_bind())
