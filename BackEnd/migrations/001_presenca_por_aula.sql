-- BackEnd/migrations/001_presenca_por_aula.sql
-- Presença por aula individual: adiciona total_aulas em chamadas e num_aula em presencas

BEGIN;

ALTER TABLE chamadas
  ADD COLUMN IF NOT EXISTS total_aulas smallint NOT NULL DEFAULT 1;

ALTER TABLE presencas
  ADD COLUMN IF NOT EXISTS num_aula smallint NOT NULL DEFAULT 1;

ALTER TABLE presencas
  DROP CONSTRAINT IF EXISTS presencas_chamada_id_aluno_id_key;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    JOIN pg_namespace n ON t.relnamespace = n.oid
    WHERE c.conname = 'presencas_chamada_aluno_aula_key'
      AND n.nspname = current_schema()
  ) THEN
    ALTER TABLE presencas
      ADD CONSTRAINT presencas_chamada_aluno_aula_key
        UNIQUE (chamada_id, aluno_id, num_aula);
  END IF;
END$$;

COMMIT;
