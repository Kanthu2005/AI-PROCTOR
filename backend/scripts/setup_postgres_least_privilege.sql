-- ==============================================================================
-- ProctorAI - Dedicated PostgreSQL Database & Least-Privilege Role Setup
-- ==============================================================================
-- IMPORTANT SAFETY RULES:
-- 1. Never commit real production passwords to source control.
-- 2. Never drop or alter existing databases or roles outside of ProctorAI.
-- 3. Replace '<CHANGE_TO_YOUR_SECURE_PASSWORD>' before running in your environment.
-- ==============================================================================

-- 1. Create Dedicated ProctorAI Application Database
SELECT 'CREATE DATABASE proctorai_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'proctorai_db')\gexec

-- 2. Create Dedicated Least-Privilege Application Role/User
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE rolname = 'proctorai_user') THEN
      CREATE ROLE proctorai_user WITH LOGIN ENCRYPTED PASSWORD '<CHANGE_TO_YOUR_SECURE_PASSWORD>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;
   END IF;
END
$do$;

-- 3. Restrict Default Public Connect Privileges on Dedicated DB
REVOKE ALL ON DATABASE proctorai_db FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE proctorai_db TO proctorai_user;

-- 4. Switch context to proctorai_db and Grant Table/Schema Privileges
\connect proctorai_db

-- Allow proctorai_user usage on the public schema
GRANT USAGE, CREATE ON SCHEMA public TO proctorai_user;

-- Ensure proctorai_user has full privileges on tables/sequences in proctorai_db schema
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO proctorai_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO proctorai_user;

-- Ensure future tables/sequences created in proctorai_db are accessible
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO proctorai_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO proctorai_user;

-- Verification query
SELECT current_database(), current_user;
