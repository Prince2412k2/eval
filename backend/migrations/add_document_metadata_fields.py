"""
Add document metadata fields

Adds file_size, page_count, chunk_count, and status columns to documents table
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Add new columns to documents table
    op.add_column('documents', sa.Column('file_size', sa.Integer(), nullable=True), schema='public')
    op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True), schema='public')
    op.add_column('documents', sa.Column('chunk_count', sa.Integer(), nullable=True), schema='public')
    op.add_column('documents', sa.Column('status', sa.String(), nullable=True, server_default='indexed'), schema='public')


def downgrade():
    # Remove columns
    op.drop_column('documents', 'status', schema='public')
    op.drop_column('documents', 'chunk_count', schema='public')
    op.drop_column('documents', 'page_count', schema='public')
    op.drop_column('documents', 'file_size', schema='public')
