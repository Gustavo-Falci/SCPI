import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { listarTurmasCompletas } from '../services/turmasService';
import { listarProfessores } from '../services/professoresService';
import { listarHorariosTodos } from '../services/horariosService';
import { listarAlunos } from '../services/alunosService';
import { listarRelatorios } from '../services/relatoriosService';
import { extractErrorMessage } from '../services/apiClient';
import { useToastContext } from './ToastContext';

const DashboardDataContext = createContext(null);

export function DashboardDataProvider({ children }) {
  const { showError } = useToastContext();

  const [turmas, setTurmas] = useState([]);
  const [professores, setProfessores] = useState([]);
  const [grade, setGrade] = useState([]);
  const [alunos, setAlunos] = useState([]);
  const [relatorios, setRelatorios] = useState([]);

  const [loading, setLoading] = useState(false);
  const [loadingRelatorios, setLoadingRelatorios] = useState(false);

  // Filtros globais
  const [filterTurno, setFilterTurno] = useState('Matutino');
  const [filterSemestre, setFilterSemestre] = useState('Todos');
  const [searchTerm, setSearchTerm] = useState('');

  const refetchTurmasProfsGrade = useCallback(async () => {
    setLoading(true);
    try {
      const [t, p, g] = await Promise.all([
        listarTurmasCompletas(),
        listarProfessores(),
        listarHorariosTodos(),
      ]);
      setTurmas(t);
      setProfessores(p);
      setGrade(g);
    } catch (err) {
      console.error(err);
      showError(`Falha ao carregar dados do painel: ${extractErrorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  const refetchAlunos = useCallback(async () => {
    try {
      const a = await listarAlunos();
      setAlunos(a);
    } catch (err) {
      console.error(err);
      showError(`Falha ao carregar alunos: ${extractErrorMessage(err)}`);
    }
  }, [showError]);

  const refetchRelatorios = useCallback(async () => {
    setLoadingRelatorios(true);
    try {
      const r = await listarRelatorios();
      setRelatorios(r);
    } catch (err) {
      console.error(err);
      showError(`Falha ao carregar relatórios: ${extractErrorMessage(err)}`);
    } finally {
      setLoadingRelatorios(false);
    }
  }, [showError]);

  useEffect(() => {
    refetchTurmasProfsGrade();
  }, [refetchTurmasProfsGrade]);

  const value = {
    turmas, professores, grade, alunos, relatorios,
    loading, loadingRelatorios,
    refetchTurmasProfsGrade, refetchAlunos, refetchRelatorios,
    filterTurno, setFilterTurno,
    filterSemestre, setFilterSemestre,
    searchTerm, setSearchTerm,
  };

  return (
    <DashboardDataContext.Provider value={value}>
      {children}
    </DashboardDataContext.Provider>
  );
}

export function useDashboardData() {
  const ctx = useContext(DashboardDataContext);
  if (!ctx) throw new Error('useDashboardData precisa estar dentro de DashboardDataProvider');
  return ctx;
}
