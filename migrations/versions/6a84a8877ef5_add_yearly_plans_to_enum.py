"""add yearly plans to enum.

Revision ID: 6a84a8877ef5
Revises: 7446b8bbc888
Create Date: 2018-10-05 19:03:17.567645

"""

# revision identifiers, used by Alembic.
revision = '6a84a8877ef5'
down_revision = '7446b8bbc888'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("ALTER TYPE plans RENAME TO plans_previous")
    op.execute("CREATE TYPE plans AS ENUM ('v1_free', 'v1_gold', 'v1_gold_yearly', 'v1_platinum', 'v1_platinum_yearly')")
    op.execute("ALTER TABLE users RENAME COLUMN plan TO plan_previous")
    op.execute("ALTER TABLE users ADD COLUMN plan plans NOT NULL DEFAULT 'v1_free'")
    op.execute("UPDATE users SET plan = plan_previous::text::plans")
    op.execute("ALTER TABLE users DROP COLUMN plan_previous")
    op.execute("DROP TYPE plans_previous")

def downgrade():
    op.execute("ALTER TYPE plans RENAME TO plans_previous")
    op.execute("CREATE TYPE plans AS ENUM ('v1_free', 'v1_gold', 'v1_platinum')")
    op.execute("ALTER TABLE users RENAME COLUMN plan TO plan_previous")
    op.execute("ALTER TABLE users ADD COLUMN plan plans NOT NULL DEFAULT 'v1_free'")
    op.execute("UPDATE users SET plan = plan_previous::text::plans")
    op.execute("ALTER TABLE users DROP COLUMN plan_previous")
    op.execute("DROP TYPE plans_previous")
