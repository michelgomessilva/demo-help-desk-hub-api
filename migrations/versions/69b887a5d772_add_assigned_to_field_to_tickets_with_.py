"""Add assigned_to field to tickets with foreing key

Revision ID: 69b887a5d772
Revises: 05d6a98dc1c6
Create Date: 2026-04-30 21:20:59.901599

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69b887a5d772'
down_revision: Union[str, Sequence[str], None] = '05d6a98dc1c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Aplicar a mudança: adicionar campo 'assigned_to' com foreign key.

    Esta é uma migration MANUAL que demonstra:
    1. Como adicionar uma coluna com tipo Integer
    2. Como criar uma constraint de foreign key
    3. Como criar um índice para melhorar performance

    O campo 'assigned_to' referencia a tabela 'users' permitindo
    atribuir tickets a usuários específicos do sistema.
    O campo é opcional (nullable=True) para não quebrar tickets existentes.
    """
    # Passo 1: Adicionar a coluna 'assigned_to' à tabela 'tickets'
    # Tipo Integer para referenciar o ID de um usuário
    # nullable=True para permitir tickets sem atribuição inicial
    op.add_column(
        'tickets',
        sa.Column('assigned_to', sa.Integer(), nullable=True)
    )

    # Passo 2: Criar a constraint de foreign key
    # Conecta 'assigned_to' em 'tickets' com 'id' em 'users'
    # ondelete='SET NULL' significa: se usuário for deletado, coloca NULL em assigned_to
    op.create_foreign_key(
        constraint_name='fk_tickets_assigned_to_users_id',
        source_table='tickets',
        referent_table='users',
        local_cols=['assigned_to'],
        remote_cols=['id'],
        ondelete='SET NULL'
    )

    # Passo 3: Criar índice para melhorar performance de buscas
    # Quando fazer queries do tipo: WHERE assigned_to = user_id
    op.create_index(
        index_name='idx_tickets_assigned_to',
        table_name='tickets',
        columns=['assigned_to']
    )


def downgrade() -> None:
    """
    Desfazer a mudança: remover o campo 'assigned_to' e suas dependências.

    Reverte todas as operações do upgrade na ordem INVERSA:
    1. Remover índice
    2. Remover foreign key
    3. Remover coluna

    ⚠️ Cuidado: Esta operação deleta as informações de atribuição!
    """
    # Passo 1: Remover o índice PRIMEIRO
    # Índices devem ser removidos antes de remover a coluna
    op.drop_index(
        index_name='idx_tickets_assigned_to',
        table_name='tickets'
    )

    # Passo 2: Remover a constraint de foreign key
    # Constraints devem ser removidas antes de remover a coluna
    op.drop_constraint(
        constraint_name='fk_tickets_assigned_to_users_id',
        table_name='tickets'
    )

    # Passo 3: Remover a coluna 'assigned_to'
    # Só remove a coluna após remover índices e constraints
    op.drop_column('tickets', 'assigned_to')