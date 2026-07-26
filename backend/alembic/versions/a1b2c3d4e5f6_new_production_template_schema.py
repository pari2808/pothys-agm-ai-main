"""new production template schema

Revision ID: a1b2c3d4e5f6
Revises: 3353bd0d000b
Create Date: 2026-07-25

Redesign database schema for new production manager Excel template.
Safely updates PostgreSQL schema by inspecting existing columns before adding/dropping.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3353bd0d000b'
branch_labels = None
depends_on = None

def get_table_columns(table_name: str):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return [c['name'] for c in insp.get_columns(table_name)]

def upgrade() -> None:
    # ── employee_performances ──
    emp_cols = get_table_columns('employee_performances')
    
    # Add new columns if missing
    new_emp_cols = [
        ('gold', sa.Numeric(15, 2)),
        ('diamond', sa.Numeric(15, 2)),
        ('platinum', sa.Numeric(15, 2)),
        ('silver', sa.Numeric(15, 2)),
        ('silver_mrp', sa.Numeric(15, 2)),
        ('subhiksham_count', sa.Integer()),
        ('subhiksham_value', sa.Numeric(15, 2)),
        ('viruksham_count', sa.Integer()),
        ('viruksham_value', sa.Numeric(15, 2)),
        ('digigold', sa.Integer()),
        ('digisilver', sa.Integer()),
    ]
    for col_name, col_type in new_emp_cols:
        if col_name not in emp_cols:
            op.add_column('employee_performances', sa.Column(col_name, col_type, server_default='0', nullable=True))

    # Migrate existing data if old columns exist
    if 'gold_amount' in emp_cols:
        op.execute("UPDATE employee_performances SET gold = COALESCE(gold_amount, 0) WHERE gold_amount IS NOT NULL")
    if 'diamond_amount' in emp_cols:
        op.execute("UPDATE employee_performances SET diamond = COALESCE(diamond_amount, 0) WHERE diamond_amount IS NOT NULL")
    if 'platinum_amount' in emp_cols:
        op.execute("UPDATE employee_performances SET platinum = COALESCE(platinum_amount, 0) WHERE platinum_amount IS NOT NULL")
    if 'silver_amount' in emp_cols:
        op.execute("UPDATE employee_performances SET silver = COALESCE(silver_amount, 0) WHERE silver_amount IS NOT NULL")
    if 'digigold_enrollments' in emp_cols:
        op.execute("UPDATE employee_performances SET digigold = COALESCE(digigold_enrollments, 0) WHERE digigold_enrollments IS NOT NULL")
    if 'digisilver_enrollments' in emp_cols:
        op.execute("UPDATE employee_performances SET digisilver = COALESCE(digisilver_enrollments, 0) WHERE digisilver_enrollments IS NOT NULL")

    # Drop old columns if exist
    old_emp_cols = ['gold_grams_sold', 'gold_amount', 'silver_grams_sold', 'silver_amount', 
                    'platinum_amount', 'diamond_amount', 'digigold_enrollments', 'digisilver_enrollments']
    for old_col in old_emp_cols:
        if old_col in emp_cols:
            op.drop_column('employee_performances', old_col)

    # ── daily_reports ──
    rep_cols = get_table_columns('daily_reports')

    new_rep_cols = [
        ('gold', sa.Numeric(15, 2)),
        ('diamond', sa.Numeric(15, 2)),
        ('platinum', sa.Numeric(15, 2)),
        ('silver', sa.Numeric(15, 2)),
        ('digigold', sa.Integer()),
        ('digisilver', sa.Integer()),
    ]
    for col_name, col_type in new_rep_cols:
        if col_name not in rep_cols:
            op.add_column('daily_reports', sa.Column(col_name, col_type, server_default='0', nullable=True))

    if 'silver_mrp' not in rep_cols:
        op.add_column('daily_reports', sa.Column('silver_mrp', sa.Numeric(15, 2), server_default='0', nullable=True))
    else:
        # If silver_mrp exists (e.g. as varchar), alter type to numeric safely
        op.execute("""
            ALTER TABLE daily_reports 
            ALTER COLUMN silver_mrp TYPE NUMERIC(15, 2) 
            USING (CASE WHEN silver_mrp IS NULL OR silver_mrp = '' THEN 0 ELSE silver_mrp::numeric END);
        """)

    # Migrate existing data if old columns exist
    if 'gold_sales' in rep_cols:
        op.execute("UPDATE daily_reports SET gold = COALESCE(gold_sales, 0) WHERE gold_sales IS NOT NULL")
    if 'diamond_sales' in rep_cols:
        op.execute("UPDATE daily_reports SET diamond = COALESCE(diamond_sales, 0) WHERE diamond_sales IS NOT NULL")
    if 'platinum_sales' in rep_cols:
        op.execute("UPDATE daily_reports SET platinum = COALESCE(platinum_sales, 0) WHERE platinum_sales IS NOT NULL")
    if 'silver_sales' in rep_cols:
        op.execute("UPDATE daily_reports SET silver = COALESCE(silver_sales, 0) WHERE silver_sales IS NOT NULL")
    if 'digigold_enrollments' in rep_cols:
        op.execute("UPDATE daily_reports SET digigold = COALESCE(digigold_enrollments, 0) WHERE digigold_enrollments IS NOT NULL")
    if 'digisilver_enrollments' in rep_cols:
        op.execute("UPDATE daily_reports SET digisilver = COALESCE(digisilver_enrollments, 0) WHERE digisilver_enrollments IS NOT NULL")

    # Drop old columns if exist
    old_rep_cols = ['gold_sales', 'silver_sales', 'platinum_sales', 'diamond_sales', 
                    'gold_weight', 'diamond_weight', 'platinum_weight', 'silver_weight', 
                    'digigold_enrollments', 'digisilver_enrollments']
    for old_col in old_rep_cols:
        if old_col in rep_cols:
            op.drop_column('daily_reports', old_col)

    # ── scheme_summaries ──
    sch_cols = get_table_columns('scheme_summaries')

    new_sch_cols = [
        ('subhiksham_count', sa.Integer()),
        ('subhiksham_value', sa.Numeric(15, 2)),
        ('viruksham_count', sa.Integer()),
        ('viruksham_value', sa.Numeric(15, 2)),
    ]
    for col_name, col_type in new_sch_cols:
        if col_name not in sch_cols:
            op.add_column('scheme_summaries', sa.Column(col_name, col_type, server_default='0', nullable=True))

    old_sch_cols = ['digigold_total', 'digisilver_total', 'digigold_revenue', 'digisilver_revenue']
    for old_col in old_sch_cols:
        if old_col in sch_cols:
            op.drop_column('scheme_summaries', old_col)


def downgrade() -> None:
    pass
