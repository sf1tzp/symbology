"""add model_configs and generated_content tables

Revision ID: 147f0cde7694
Revises: 2cfa71d62a61
Create Date: 2025-08-04 12:00:32.936548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '147f0cde7694'
down_revision: Union[str, Sequence[str], None] = '2cfa71d62a61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create new enum type for content source type (check if exists first)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE content_source_type_enum AS ENUM ('DOCUMENTS', 'GENERATED_CONTENT', 'BOTH');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create model_configs table
    op.create_table('model_configs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('options_json', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_configs_name'), 'model_configs', ['name'], unique=False)

    # Create generated_content table using raw SQL to avoid enum issues
    op.execute("""
        CREATE TABLE generated_content (
            id UUID NOT NULL,
            content_hash VARCHAR(64),
            company_id UUID,
            document_type document_type_enum,
            source_type content_source_type_enum NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            total_duration FLOAT,
            content TEXT,
            summary TEXT,
            model_config_id UUID,
            system_prompt_id UUID,
            user_prompt_id UUID,
            CONSTRAINT pk_generated_content PRIMARY KEY (id),
            CONSTRAINT fk_generated_content_company_id FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
            CONSTRAINT fk_generated_content_model_config_id FOREIGN KEY(model_config_id) REFERENCES model_configs(id) ON DELETE SET NULL,
            CONSTRAINT fk_generated_content_system_prompt_id FOREIGN KEY(system_prompt_id) REFERENCES prompts(id) ON DELETE SET NULL,
            CONSTRAINT fk_generated_content_user_prompt_id FOREIGN KEY(user_prompt_id) REFERENCES prompts(id) ON DELETE SET NULL
        )
    """)
    op.create_index(op.f('ix_generated_content_company_id'), 'generated_content', ['company_id'], unique=False)
    op.create_index(op.f('ix_generated_content_content_hash'), 'generated_content', ['content_hash'], unique=True)
    op.create_index(op.f('ix_generated_content_model_config_id'), 'generated_content', ['model_config_id'], unique=False)
    op.create_index(op.f('ix_generated_content_system_prompt_id'), 'generated_content', ['system_prompt_id'], unique=False)
    op.create_index(op.f('ix_generated_content_user_prompt_id'), 'generated_content', ['user_prompt_id'], unique=False)
    op.create_table('generated_content_source_association',
    sa.Column('parent_content_id', sa.Uuid(), nullable=False),
    sa.Column('source_content_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['parent_content_id'], ['generated_content.id'], ),
    sa.ForeignKeyConstraint(['source_content_id'], ['generated_content.id'], ),
    sa.PrimaryKeyConstraint('parent_content_id', 'source_content_id')
    )
    op.create_table('generated_content_document_association',
    sa.Column('generated_content_id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.ForeignKeyConstraint(['generated_content_id'], ['generated_content.id'], ),
    sa.PrimaryKeyConstraint('generated_content_id', 'document_id')
    )
    op.alter_column('aggregates', 'num_ctx',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Integer(),
               existing_nullable=True)
    op.drop_index(op.f('idx_aggregates_company_id'), table_name='aggregates')
    op.create_index(op.f('ix_aggregates_company_id'), 'aggregates', ['company_id'], unique=False)
    op.alter_column('completions', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('completions', 'total_duration',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=True)
    op.alter_column('completions', 'top_k',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=True)
    op.alter_column('completions', 'num_ctx',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=True)
    op.drop_index(op.f('ix_completions_user_prompt_id'), table_name='completions')
    op.drop_constraint(op.f('completions_user_prompt_id_fkey'), 'completions', type_='foreignkey')
    op.drop_constraint(op.f('completions_system_prompt_id_fkey'), 'completions', type_='foreignkey')
    op.create_foreign_key(None, 'completions', 'prompts', ['system_prompt_id'], ['id'], ondelete='SET NULL')
    op.drop_column('completions', 'user_prompt_id')
    op.alter_column('prompts', 'content',
               existing_type=sa.TEXT(),
               nullable=False)
    op.add_column('ratings', sa.Column('aggregate_id', sa.Uuid(), nullable=True))
    op.alter_column('ratings', 'completion_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.create_index(op.f('ix_ratings_aggregate_id'), 'ratings', ['aggregate_id'], unique=False)
    op.create_foreign_key(None, 'ratings', 'aggregates', ['aggregate_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'ratings', type_='foreignkey')
    op.drop_index(op.f('ix_ratings_aggregate_id'), table_name='ratings')
    op.alter_column('ratings', 'completion_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('ratings', 'aggregate_id')
    op.alter_column('prompts', 'content',
               existing_type=sa.TEXT(),
               nullable=True)
    op.add_column('completions', sa.Column('user_prompt_id', sa.UUID(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'completions', type_='foreignkey')
    op.create_foreign_key(op.f('completions_system_prompt_id_fkey'), 'completions', 'prompts', ['system_prompt_id'], ['id'])
    op.create_foreign_key(op.f('completions_user_prompt_id_fkey'), 'completions', 'prompts', ['user_prompt_id'], ['id'])
    op.create_index(op.f('ix_completions_user_prompt_id'), 'completions', ['user_prompt_id'], unique=False)
    op.alter_column('completions', 'num_ctx',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('completions', 'top_k',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('completions', 'total_duration',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('completions', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.drop_index(op.f('ix_aggregates_company_id'), table_name='aggregates')
    op.create_index(op.f('idx_aggregates_company_id'), 'aggregates', ['company_id'], unique=False)
    op.alter_column('aggregates', 'num_ctx',
               existing_type=sa.Integer(),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.drop_table('generated_content_document_association')
    op.drop_table('generated_content_source_association')
    op.drop_index(op.f('ix_generated_content_user_prompt_id'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_system_prompt_id'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_model_config_id'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_content_hash'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_company_id'), table_name='generated_content')
    op.drop_table('generated_content')
    op.drop_index(op.f('ix_model_configs_name'), table_name='model_configs')
    op.drop_table('model_configs')
    # ### end Alembic commands ###
