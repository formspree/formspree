"""replace .upgraded with .plan

Revision ID: 20697541f4cf
Revises: a156683c29f2
Create Date: 2018-09-12 18:52:14.025894

"""

# revision identifiers, used by Alembic.
revision = '20697541f4cf'
down_revision = 'a156683c29f2'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM

plans = ENUM('v1_free', 'v1_gold', 'v1_platinum', name='plans', create_type=False)

def upgrade():
    op.create_table('email_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('form_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.Text(), nullable=False),
        sa.Column('from_name', sa.Text(), nullable=False),
        sa.Column('style', sa.Text(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('form_id')
    )
    plans.create(op.get_bind(), checkfirst=True)
    op.add_column('users', sa.Column('plan', plans, nullable=True))
    op.execute("UPDATE users SET plan = 'v1_gold' WHERE upgraded")
    op.execute("UPDATE users SET plan = 'v1_free' WHERE NOT upgraded")
    op.alter_column('users', 'plan', nullable=False)
    op.drop_column('users', 'upgraded')


def downgrade():
    op.add_column('users', sa.Column('upgraded', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.execute("UPDATE users SET upgraded = true WHERE plan != 'v1_free'")
    op.execute("UPDATE users SET upgraded = false WHERE plan = 'v1_free'")
    op.drop_column('users', 'plan')
    plans.drop(op.get_bind())
    op.drop_table('email_templates')
