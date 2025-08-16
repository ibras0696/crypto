"""add kyc data table

Revision ID: 0002_kyc_data
Revises: 0001_initial
Create Date: 2025-08-15
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0002_kyc_data'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'kyc_data',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('document_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table('kyc_data')
