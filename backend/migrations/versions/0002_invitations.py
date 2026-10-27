"""Organization invitation lifecycle."""
from alembic import op
from backend.models import OrganizationInvitation
revision='0002'
down_revision='0001'
def upgrade():OrganizationInvitation.__table__.create(bind=op.get_bind(),checkfirst=True)
def downgrade():OrganizationInvitation.__table__.drop(bind=op.get_bind(),checkfirst=True)
