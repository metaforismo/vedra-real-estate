-- Run once as the project database administrator, not from the public frontend.
-- Set the password privately with psql \password vedra_app (do not commit passwords).
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vedra_app') THEN
    CREATE ROLE vedra_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;
CREATE SCHEMA IF NOT EXISTS vedra AUTHORIZATION vedra_app;
REVOKE ALL ON SCHEMA vedra FROM PUBLIC, anon, authenticated;
GRANT CONNECT ON DATABASE postgres TO vedra_app;
ALTER DEFAULT PRIVILEGES FOR ROLE vedra_app IN SCHEMA vedra
  REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE vedra_app IN SCHEMA vedra
  REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
-- Do not add vedra to the Supabase Data API's exposed schemas.
-- API and worker connect with vedra_app, never with a browser service-role key.
