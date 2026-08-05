-- Verificação dos 6 índices do P3 (PR #90) DEPOIS de uma aula real.
-- Rodar no DBeaver, conectado ao banco `scpi` da VM de produção.
--
-- Só faz sentido depois que uma chamada de verdade abriu, registrou presenças e
-- fechou: idx_scan é contador acumulado desde o último reset das estatísticas,
-- e um índice recém-criado começa em 0 mesmo estando perfeito.

-- 1) Quanto cada índice do P3 foi usado.
--    idx_scan = 0 depois de uma aula é o achado: ou a query não bate com o
--    índice, ou a tabela é pequena demais e o planner prefere seq scan.
SELECT s.relname                                   AS tabela,
       s.indexrelname                              AS indice,
       s.idx_scan                                  AS varreduras,
       s.idx_tup_read                              AS tuplas_lidas,
       s.idx_tup_fetch                             AS tuplas_buscadas,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho
  FROM pg_stat_user_indexes s
 WHERE s.indexrelname IN (
           'idx_horarios_sala_dia',
           'idx_horarios_turma',
           'idx_presencas_aluno',
           'idx_chamadas_turma_status',
           'idx_chamadas_professor',
           'idx_chamadas_data'
       )
 ORDER BY s.idx_scan DESC, s.indexrelname;

-- 2) Contexto: seq scan x index scan por tabela.
--    seq_scan alto com n_live_tup baixo é normal — o planner ignora índice em
--    tabela pequena, e isso não invalida o índice, só adia o ganho.
SELECT relname     AS tabela,
       seq_scan    AS varreduras_sequenciais,
       seq_tup_read,
       idx_scan    AS varreduras_por_indice,
       n_live_tup  AS linhas_vivas
  FROM pg_stat_user_tables
 WHERE lower(relname) IN ('horarios_aulas', 'presencas', 'chamadas', 'turma_alunos')
 ORDER BY relname;

-- 3) Desde quando os contadores acumulam. Se o reset for recente, a leitura de
--    cima cobre menos tempo do que parece.
SELECT stats_reset FROM pg_stat_database WHERE datname = current_database();

-- 4) Prova direta, independente do contador: o planner escolhe o índice?
--    Trocar os literais por uma sala/dia que existam. Esperado no plano:
--    "Index Scan using idx_horarios_sala_dia" — "Seq Scan" aqui é o sinal ruim.
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM horarios_aulas WHERE sala = 'Sala 101' AND dia_semana = 1;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM Chamadas WHERE turma_id = 1 AND status = 'Aberta';
