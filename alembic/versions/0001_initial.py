"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-08-15
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='user'),
        sa.Column('kyc_status', sa.String(20), nullable=False, server_default='unverified'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table('currencies',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('code', sa.String(20), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('reserve', sa.Numeric(18,8), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table('orders',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('from_currency', sa.Integer, sa.ForeignKey('currencies.id')),
        sa.Column('to_currency', sa.Integer, sa.ForeignKey('currencies.id')),
        sa.Column('amount_from', sa.Numeric(18,8), nullable=False),
        sa.Column('amount_to', sa.Numeric(18,8), nullable=False),
        sa.Column('wallet_address', sa.String(120)),
        sa.Column('payout_details', sa.String(255)),
        sa.Column('rate', sa.Numeric(18,8), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table('transactions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('order_id', sa.Integer, sa.ForeignKey('orders.id', ondelete='CASCADE')),
        sa.Column('tx_hash', sa.String(120)),
        sa.Column('amount', sa.Numeric(18,8), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('details', sa.String(255)),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

def downgrade():
    op.drop_table('audit_logs')
    op.drop_table('transactions')
    op.drop_table('orders')
    op.drop_table('currencies')
    op.drop_table('users')
