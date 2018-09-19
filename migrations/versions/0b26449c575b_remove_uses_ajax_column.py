"""remove uses_ajax column.

Revision ID: ba751c319377
Revises: 20697541f4cf
Create Date: 2018-09-19 00:06:41.940239

"""

# revision identifiers, used by Alembic.
revision = 'ba751c319377'
down_revision = '20697541f4cf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('forms', 'uses_ajax')


def downgrade():
    op.add_column('forms', sa.Column('uses_ajax', sa.Boolean))
