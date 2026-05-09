-- BackEnd/migrations/001_presenca_por_aula.sql

-- Chamadas: quantas aulas tem essa sessão
ALTER TABLE chamadas
  ADD COLUMN IF NOT EXISTS total_aulas smallint NOT NULL DEFAULT 1;

-- Presencas: qual aula dentro da sessão
ALTER TABLE presencas
  ADD COLUMN IF NOT EXISTS num_aula smallint NOT NULL DEFAULT 1;

-- Troca constraint UNIQUE
ALTER TABLE presencas
  DROP CONSTRAINT IF EXISTS presencas_chamada_id_aluno_id_key;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'presencas_chamada_aluno_aula_key'
  ) THEN
    ALTER TABLE presencas
      ADD CONSTRAINT presencas_chamada_aluno_aula_key
        UNIQUE (chamada_id, aluno_id, num_aula);
  END IF;
END$$;
