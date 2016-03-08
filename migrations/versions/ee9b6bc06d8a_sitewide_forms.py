"""sitewide forms.

Revision ID: ee9b6bc06d8a
Revises: 2580663da150
Create Date: 2016-03-07 19:59:20.392152

"""

# revision identifiers, used by Alembic.
revision = 'ee9b6bc06d8a'
down_revision = '2580663da150'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('forms', sa.Column('sitewide', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('forms', 'sitewide')
