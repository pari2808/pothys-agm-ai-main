"""add category to notifications

Revision ID: ff9f23a6ab73
Revises: a1b2c3d4e5f6
Create Date: 2026-07-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff9f23a6ab73'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c['name'] for c in insp.get_columns('notifications')]
    if 'category' not in columns:
        op.add_column('notifications', sa.Column('category', sa.String(length=50), server_default='Updates', nullable=False))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c['name'] for c in insp.get_columns('notifications')]
    if 'category' in columns:
        op.drop_column('notifications', 'category')
