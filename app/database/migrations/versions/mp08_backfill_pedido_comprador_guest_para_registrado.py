"""Backfill: pedidos marketplace com comprador GUEST → consumidor REGISTERED (mesmo e-mail).

Corrige histórico em que checkout criou comprador guest enquanto o cliente estava logado com
conta REGISTERED `tenant_id` NULL (mesmo e-mail). Novos fluxos já corrigidos em código.

Revision ID: mp08_pedido_comprador_registered_backfill
Revises: mv15_anuncio_og_image_url
"""

from alembic import op

revision = "mp08_pedido_comprador_registered_backfill"
down_revision = "mv15_anuncio_og_image_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH guest_pedidos AS (
            SELECT pm.id AS pedido_id,
                   pm.tenant_id AS pedido_tenant,
                   lower(trim(g.email)) AS email_norm
            FROM pedidos_marketplace pm
            INNER JOIN consumidores_marketplace g ON g.id = pm.comprador_id
            WHERE g.deleted_at IS NULL
              AND g.tipo_consumidor = 'GUEST'
        ),
        resolved AS (
            SELECT gp.pedido_id,
                   (
                       SELECT c.id
                       FROM consumidores_marketplace c
                       WHERE c.deleted_at IS NULL
                         AND lower(trim(c.email)) = gp.email_norm
                         AND c.tipo_consumidor = 'REGISTERED'
                         AND (c.tenant_id IS NULL OR c.tenant_id = gp.pedido_tenant)
                       ORDER BY
                         CASE WHEN c.tenant_id IS NOT DISTINCT FROM gp.pedido_tenant THEN 0 ELSE 1 END,
                         c.id
                       LIMIT 1
                   ) AS registered_id
            FROM guest_pedidos gp
        )
        UPDATE pedidos_marketplace pm
        SET comprador_id = r.registered_id,
            updated_at = now()
        FROM resolved r
        WHERE pm.id = r.pedido_id
          AND r.registered_id IS NOT NULL
          AND pm.comprador_id IS DISTINCT FROM r.registered_id;
        """
    )


def downgrade() -> None:
    """Backfill de dados de negócio: não há reversão segura sem tabela de auditoria."""
    pass
