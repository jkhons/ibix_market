-- PDV Ibix — Role da aplicação sem BYPASSRLS (Fase 9 / RLS efetivo)
-- Executar como superuser (postgres) UMA VEZ antes de RLS_ENABLED=true.
--
--   export PDV_APP_PASSWORD='senha_forte'
--   psql -U postgres -d pdv_solumatica -v ON_ERROR_STOP=1 \
--     -c "CREATE ROLE pdv_app LOGIN PASSWORD '$PDV_APP_PASSWORD' NOBYPASSRLS NOSUPERUSER;" \
--     -f scripts/sql/create_pdv_app_role_grants.sql

-- Ou editar a senha abaixo e rodar este arquivo inteiro:
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pdv_app') THEN
    CREATE ROLE pdv_app LOGIN PASSWORD 'ALTERAR_SENHA_AQUI' NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  ELSE
    ALTER ROLE pdv_app NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE pdv_solumatica TO pdv_app;
GRANT USAGE ON SCHEMA public TO pdv_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pdv_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pdv_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pdv_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO pdv_app;

-- Depois: .env → DB_USER=pdv_app, DB_PASSWORD=..., RLS_ENABLED=true, reiniciar serviços.
