import React, { useState, useEffect, useRef } from 'react';
import {
  Users, BookOpen, Calendar, Plus, Trash2, ChevronRight, ChevronDown, LogOut,
  LayoutDashboard, Clock, MapPin, Upload, FileText, CheckCircle2, Lock,
  Filter, Sun, Moon, GraduationCap, Search, UserPlus, X, UserCog, AlertTriangle
} from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://10.34.221.165:8000';

// --- Gerenciamento de refresh token (singleton) ---
// Evita múltiplas chamadas concorrentes de /auth/refresh: se uma requisição de
// refresh já está em andamento, outras requisições esperam a mesma Promise.
let refreshPromise = null;

function clearAdminSession() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_refresh_token');
  localStorage.removeItem('admin_user');
}

async function tryRefreshAdminToken() {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refresh = localStorage.getItem('admin_refresh_token');
    if (!refresh) return null;
    try {
      // Usa axios "cru" para evitar recursão no interceptor de resposta.
      const response = await axios.post(
        `${API_URL}/auth/refresh`,
        { refresh_token: refresh },
        { headers: { 'Content-Type': 'application/json' } }
      );
      const data = response.data;
      if (data?.access_token && data?.refresh_token) {
        localStorage.setItem('admin_token', data.access_token);
        localStorage.setItem('admin_refresh_token', data.refresh_token);
        return data.access_token;
      }
      return null;
    } catch {
      return null;
    }
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

// Slots oficiais da grade ADS Fatec
const SLOTS_MATUTINO = [
  { id: 1, inicio: '07:40', fim: '08:30' },
  { id: 2, inicio: '08:30', fim: '09:20' },
  { id: 3, inicio: '09:30', fim: '10:20' },
  { id: 4, inicio: '10:20', fim: '11:10' },
  { id: 5, inicio: '11:20', fim: '12:10' },
  { id: 6, inicio: '12:10', fim: '13:00' },
];
const SLOTS_NOTURNO = [
  { id: 1, inicio: '18:45', fim: '19:35' },
  { id: 2, inicio: '19:35', fim: '20:25' },
  { id: 3, inicio: '20:25', fim: '21:15' },
  { id: 4, inicio: '21:25', fim: '22:15' },
  { id: 5, inicio: '22:15', fim: '23:05' },
];
const getSlots = (turno) => turno === 'Noturno' ? SLOTS_NOTURNO : SLOTS_MATUTINO;

export default function AdminPortal() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [adminUser, setAdminUser] = useState(null);

  // Callback chamado quando o refresh falha (sessão expirada irrecuperável).
  // Definido como ref para manter a mesma referência estável no interceptor,
  // mas sempre executar a lógica mais recente.
  const onSessionExpiredRef = useRef(() => {
    clearAdminSession();
    setIsLoggedIn(false);
    setAdminUser(null);
  });
  onSessionExpiredRef.current = () => {
    clearAdminSession();
    setIsLoggedIn(false);
    setAdminUser(null);
  };

  // Restaura sessão previamente salva no localStorage.
  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    const refresh = localStorage.getItem('admin_refresh_token');
    const user = localStorage.getItem('admin_user');
    if (token && refresh && user) {
      try {
        setAdminUser(JSON.parse(user));
        setIsLoggedIn(true);
      } catch {
        clearAdminSession();
      }
    } else if (token || refresh || user) {
      // Estado inconsistente (ex.: token antigo sem refresh) — limpa para forçar novo login.
      clearAdminSession();
    }
  }, []);

  // Interceptor axios (response): detecta 401, tenta refresh e refaz a request.
  // Registrado uma única vez no mount do app e ejetado no unmount.
  useEffect(() => {
    const interceptorId = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        const status = error.response?.status;

        // Não tenta refresh se:
        // - não há response (erro de rede puro)
        // - status != 401
        // - a própria request é do /auth/refresh ou /auth/login (evita loop)
        // - a request já foi marcada como "retried"
        if (
          status !== 401 ||
          !originalRequest ||
          originalRequest._retry ||
          originalRequest.url?.includes('/auth/refresh') ||
          originalRequest.url?.includes('/auth/login')
        ) {
          return Promise.reject(error);
        }

        originalRequest._retry = true;

        const newToken = await tryRefreshAdminToken();
        if (!newToken) {
          onSessionExpiredRef.current?.();
          return Promise.reject(error);
        }

        // Atualiza o header Authorization da request original e reenvia.
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return axios(originalRequest);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptorId);
    };
  }, []);

  if (!isLoggedIn) {
    return <LoginScreen onLogin={(data) => {
      localStorage.setItem('admin_token', data.access_token);
      localStorage.setItem('admin_refresh_token', data.refresh_token);
      localStorage.setItem('admin_user', JSON.stringify(data));
      setAdminUser(data);
      setIsLoggedIn(true);
    }} />;
  }

  return <AdminDashboard admin={adminUser} onLogout={async () => {
    const refresh = localStorage.getItem('admin_refresh_token');
    const token = localStorage.getItem('admin_token');
    if (refresh) {
      try {
        await axios.post(
          `${API_URL}/auth/logout`,
          { refresh_token: refresh },
          { headers: { Authorization: `Bearer ${token}` } }
        );
      } catch {
        // Ignora erros — a limpeza local é autoritativa.
      }
    }
    clearAdminSession();
    setIsLoggedIn(false);
    setAdminUser(null);
  }} />;
}

// --- TELA DE LOGIN ---
function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('username', email.trim());
      params.append('password', password);
      
      const res = await axios.post(`${API_URL}/auth/login`, params.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      onLogin(res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : "Erro de conexão");
      setLoginError(`Falha no login: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0C0C12] p-6">
      <div className="w-full max-w-lg bg-[#151718] rounded-[50px] p-12 border border-white/5 shadow-2xl">
        <div className="text-center mb-12">
          <div className="w-24 h-24 bg-[#4B39EF]/10 rounded-[30px] flex items-center justify-center mx-auto mb-8">
            <Lock className="text-[#4B39EF]" size={48} />
          </div>
          <h1 className="text-4xl font-black text-white tracking-tight">Portal SCPI</h1>
          <p className="text-gray-500 text-lg mt-3 font-medium">Gestão Administrativa</p>
        </div>
        
        <form onSubmit={handleLogin} className="space-y-8">
          <div className="space-y-3">
            <label className="text-xs font-black text-gray-400 uppercase tracking-[0.2em] ml-1">E-mail de Acesso</label>
            <input 
              type="email" required
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg text-white focus:border-[#4B39EF] focus:ring-2 focus:ring-[#4B39EF]/20 outline-none transition-all placeholder:text-gray-700"
              placeholder="admin@scpi.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-3">
            <label className="text-xs font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Senha Secreta</label>
            <input 
              type="password" required
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg text-white focus:border-[#4B39EF] focus:ring-2 focus:ring-[#4B39EF]/20 outline-none transition-all placeholder:text-gray-700"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
          </div>
          <button
            disabled={loading}
            className="w-full bg-[#4B39EF] hover:bg-[#5E47FF] text-white font-black py-6 rounded-2xl shadow-2xl shadow-[#4B39EF]/40 transition-all uppercase tracking-widest text-sm active:scale-[0.98]"
          >
            {loading ? 'Processando...' : 'Entrar no Sistema'}
          </button>
          {loginError && (
            <div className="flex items-center gap-3 mt-6 px-5 py-4 rounded-2xl border border-red-500/40 bg-red-500/5">
              <X size={16} className="text-red-400 shrink-0" />
              <p className="text-sm font-bold text-red-400">{loginError}</p>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

// --- DASHBOARD PRINCIPAL ---
function AdminDashboard({ admin, onLogout }) {
  const [activeTab, setActiveTab] = useState('turmas');
  const [turmas, setTurmas] = useState([]);
  const [professores, setProfessores] = useState([]);
  const [grade, setGrade] = useState([]);
  const [loading, setLoading] = useState(false);

  // Filtros
  const [filterTurno, setFilterTurno] = useState('Matutino');
  const [filterSemestre, setFilterSemestre] = useState('Todos');
  const [searchTerm, setSearchSearchTerm] = useState('');
  const [turmaPage, setTurmaPage] = useState(1);
  const TURMAS_PER_PAGE = 6;
  const [profPage, setProfPage] = useState(1);
  const PROF_PER_PAGE = 8;
  const [alunoPage, setAlunoPage] = useState(1);
  const ALUNO_PER_PAGE = 8;
  const [relatorioPage, setRelatorioPage] = useState(1);
  const RELATORIO_PER_PAGE = 8;

  const [newTurma, setNewTurma] = useState({ professor_id: '', codigo_turma: '', nome_disciplina: '', periodo_letivo: '2025-1', sala_padrao: '', turno: 'Matutino', semestre: '1' });

  // Criação de usuários (admin)
  const [novoProfessor, setNovoProfessor] = useState({ nome: '', email: '', departamento: '' });
  const [novoAluno, setNovoAluno] = useState({ nome: '', email: '', ra: '', turno: 'Matutino' });
  const [senhaTemporariaModal, setSenhaTemporariaModal] = useState(null);
  const [alunos, setAlunos] = useState([]);

  // Modal de adicionar horário (usa slots oficiais do turno)
  const [horarioModal, setHorarioModal] = useState(null); // { dia_semana } ou null
  const [horarioForm, setHorarioForm] = useState({ turma_id: '', slot_inicio: 1, slot_fim: 1, sala: '' });

  // Modal de atribuição de professor a uma turma
  const [professorModal, setProfessorModal] = useState(null); // turma ou null
  const [selectedProfessorId, setSelectedProfessorId] = useState('');

  // Modal de matrícula individual de aluno em uma turma
  const [matriculaModal, setMatriculaModal] = useState(null); // turma ou null
  const [alunosDisponiveis, setAlunosDisponiveis] = useState([]);
  const [selectedAlunoIds, setSelectedAlunoIds] = useState(new Set());
  const [searchAluno, setSearchAluno] = useState('');
  const [loadingAlunos, setLoadingAlunos] = useState(false);

  // Relatórios
  const [relatorios, setRelatorios] = useState([]);
  const [loadingRelatorios, setLoadingRelatorios] = useState(false);
  const [relatorioExpandido, setRelatorioExpandido] = useState(null);

  const fetchRelatorios = async () => {
    setLoadingRelatorios(true);
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.get(`${API_URL}/admin/relatorios/chamadas`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRelatorios(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingRelatorios(false);
    }
  };

  const fetchAlunos = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.get(`${API_URL}/admin/alunos`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAlunos(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateProfessor = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.post(`${API_URL}/admin/usuarios/professor`, novoProfessor, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSenhaTemporariaModal({ nome: novoProfessor.nome, senha: res.data.senha_temporaria, tipo: 'Professor' });
      setNovoProfessor({ nome: '', email: '', departamento: '' });
      fetchData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      showToast(`Erro ao criar professor: ${typeof detail === 'string' ? detail : 'Falha no servidor'}`, 'error');
    }
  };

  const handleCreateAluno = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.post(`${API_URL}/admin/usuarios/aluno`, novoAluno, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSenhaTemporariaModal({ nome: novoAluno.nome, senha: res.data.senha_temporaria, tipo: 'Aluno' });
      setNovoAluno({ nome: '', email: '', ra: '', turno: 'Matutino' });
      fetchAlunos();
    } catch (err) {
      const detail = err.response?.data?.detail;
      showToast(`Erro ao criar aluno: ${typeof detail === 'string' ? detail : 'Falha no servidor'}`, 'error');
    }
  };

  const handleOpenRelatorioDetalhe = async (chamada_id) => {
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.get(`${API_URL}/admin/relatorios/chamadas/${chamada_id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRelatorioExpandido(res.data);
    } catch (err) {
      showToast('Erro ao carregar detalhe da chamada.', 'error');
    }
  };

  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });
  const showToast = (message, type = 'success') => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast(t => ({ ...t, show: false })), 3500);
  };

  const [confirmDialog, setConfirmDialog] = useState({ show: false, title: '', message: '', onConfirm: null });
  const showConfirm = (title, message, onConfirmFn) =>
    setConfirmDialog({ show: true, title, message, onConfirm: onConfirmFn });

  const openProfessorModal = (turma) => {
    setProfessorModal(turma);
    setSelectedProfessorId(turma.professor_id || '');
  };

  const handleAtribuirProfessor = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      await axios.patch(
        `${API_URL}/admin/turmas/${professorModal.turma_id}/professor`,
        { professor_id: selectedProfessorId || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setProfessorModal(null);
      fetchData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      showToast(`Erro ao atribuir professor: ${typeof detail === 'string' ? detail : 'Falha no servidor'}`, 'error');
    }
  };

  const openMatriculaModal = async (turma) => {
    setMatriculaModal(turma);
    setSelectedAlunoIds(new Set());
    setSearchAluno('');
    setLoadingAlunos(true);
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.get(`${API_URL}/admin/alunos`, {
        params: { turma_id: turma.turma_id },
        headers: { Authorization: `Bearer ${token}` },
      });
      setAlunosDisponiveis(res.data);
    } catch (err) {
      showToast('Erro ao carregar alunos.', 'error');
      setMatriculaModal(null);
    } finally {
      setLoadingAlunos(false);
    }
  };

  const toggleAluno = (aluno_id) => {
    setSelectedAlunoIds(prev => {
      const next = new Set(prev);
      if (next.has(aluno_id)) next.delete(aluno_id);
      else next.add(aluno_id);
      return next;
    });
  };

  const handleMatricular = async () => {
    if (selectedAlunoIds.size === 0) { showToast('Selecione pelo menos um aluno.', 'warning'); return; }
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.post(
        `${API_URL}/admin/turmas/${matriculaModal.turma_id}/matricular-alunos`,
        { aluno_ids: Array.from(selectedAlunoIds) },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      showToast(res.data.mensagem);
      setMatriculaModal(null);
      fetchData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      showToast(`Erro ao matricular: ${typeof detail === 'string' ? detail : 'Falha no servidor'}`, 'error');
    }
  };

  const openHorarioModal = (dia_semana) => {
    setHorarioForm({ turma_id: '', slot_inicio: 1, slot_fim: 1, sala: '' });
    setHorarioModal({ dia_semana });
  };

  const handleAddHorario = async (e) => {
    e.preventDefault();
    const slots = getSlots(filterTurno);
    const slotIni = slots.find(s => s.id === Number(horarioForm.slot_inicio));
    const slotFim = slots.find(s => s.id === Number(horarioForm.slot_fim));
    if (!slotIni || !slotFim || !horarioForm.turma_id) { showToast('Preencha turma e slots.', 'warning'); return; }
    if (slotFim.id < slotIni.id) { showToast('Slot final deve ser ≥ slot inicial.', 'warning'); return; }

    const conflito = grade.find(g =>
      g.turma_id === horarioForm.turma_id &&
      g.dia_semana === horarioModal.dia_semana &&
      slotIni.inicio < g.fim &&
      slotFim.fim > g.inicio
    );
    if (conflito) {
      showToast(`Conflito: "${conflito.nome_disciplina}" já ocupa ${conflito.inicio}–${conflito.fim} neste dia.`, 'error');
      return;
    }

    try {
      const token = localStorage.getItem('admin_token');
      await axios.post(`${API_URL}/admin/horarios`, {
        turma_id: horarioForm.turma_id,
        dia_semana: horarioModal.dia_semana,
        horario_inicio: slotIni.inicio,
        horario_fim: slotFim.fim,
        sala: horarioForm.sala,
      }, { headers: { Authorization: `Bearer ${token}` } });
      setHorarioModal(null);
      fetchData();
    } catch (err) {
      showToast('Erro ao adicionar horário', 'error');
    }
  };

  useEffect(() => { fetchData(); }, []);
  useEffect(() => { if (activeTab === 'relatorios') fetchRelatorios(); }, [activeTab]);
  useEffect(() => { if (activeTab === 'alunos') fetchAlunos(); }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('admin_token');
      const config = { headers: { Authorization: `Bearer ${token}` } };
      const [resTurmas, resProfs, resGrade] = await Promise.all([
        axios.get(`${API_URL}/admin/turmas-completas`, config),
        axios.get(`${API_URL}/admin/professores`, config),
        axios.get(`${API_URL}/admin/horarios-todos`, config)
      ]);
      setTurmas(resTurmas.data);
      setProfessores(resProfs.data);
      setGrade(resGrade.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTurma = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('admin_token');
      await axios.post(`${API_URL}/admin/turmas`, newTurma, { headers: { Authorization: `Bearer ${token}` } });
      showToast('Turma criada com sucesso!');
      setNewTurma({ ...newTurma, nome_disciplina: '', codigo_turma: '', sala_padrao: '' });
      fetchData();
    } catch (err) {
      showToast('Erro ao criar turma', 'error');
    }
  };

  const filteredTurmas = turmas.filter(t => {
    const matchTurno = t.turno === filterTurno;
    const matchSemestre = filterSemestre === 'Todos' || t.semestre === filterSemestre;
    const matchSearch = t.nome_disciplina.toLowerCase().includes(searchTerm.toLowerCase()) || t.codigo_turma.toLowerCase().includes(searchTerm.toLowerCase());
    return matchTurno && matchSemestre && matchSearch;
  });
  const turmasTotalPages = Math.max(1, Math.ceil(filteredTurmas.length / TURMAS_PER_PAGE));
  const turmasPaged = filteredTurmas.slice((turmaPage - 1) * TURMAS_PER_PAGE, turmaPage * TURMAS_PER_PAGE);

  const filteredRelatorios = relatorios.filter(r => {
    const matchTurno = r.turno === filterTurno;
    const matchSemestre = filterSemestre === 'Todos' || String(r.semestre) === filterSemestre;
    return matchTurno && matchSemestre;
  });

  const profTotalPages = Math.max(1, Math.ceil(professores.length / PROF_PER_PAGE));
  const profPaged = professores.slice((profPage - 1) * PROF_PER_PAGE, profPage * PROF_PER_PAGE);

  const alunoTotalPages = Math.max(1, Math.ceil(alunos.length / ALUNO_PER_PAGE));
  const alunosPaged = alunos.slice((alunoPage - 1) * ALUNO_PER_PAGE, alunoPage * ALUNO_PER_PAGE);

  const relatorioTotalPages = Math.max(1, Math.ceil(filteredRelatorios.length / RELATORIO_PER_PAGE));
  const relatoriosPaged = filteredRelatorios.slice((relatorioPage - 1) * RELATORIO_PER_PAGE, relatorioPage * RELATORIO_PER_PAGE);

  const handleImportCSV = async (turmaId, file) => {
    if(!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.post(`${API_URL}/admin/turmas/${turmaId}/importar-alunos`, formData, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'multipart/form-data' }
      });
      showToast(res.data.mensagem);
      fetchData();
    } catch (err) {
      showToast('Erro na importação de alunos', 'error');
    }
  };

  const handleDeleteTurma = (id) => {
    showConfirm(
      'Excluir Turma',
      'Deseja realmente excluir esta turma? Todos os alunos e horários vinculados serão removidos.',
      async () => {
        try {
          const token = localStorage.getItem('admin_token');
          await axios.delete(`${API_URL}/admin/turmas/${id}`, { headers: { Authorization: `Bearer ${token}` } });
          fetchData();
        } catch {
          showToast('Erro ao excluir turma', 'error');
        }
      }
    );
  };

  const handleDeleteProfessor = (professor_id, nome) => {
    showConfirm(
      'Excluir Professor',
      `Deseja realmente excluir o professor "${nome}"?\n\nAs disciplinas atribuídas a ele ficarão sem professor.`,
      async () => {
        try {
          const token = localStorage.getItem('admin_token');
          await axios.delete(`${API_URL}/admin/professores/${professor_id}`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          fetchData();
        } catch {
          showToast('Erro ao excluir professor', 'error');
        }
      }
    );
  };

  const handleDeleteHorario = (id) => {
    showConfirm(
      'Excluir Horário',
      'Deseja realmente remover esta aula da grade semanal?',
      async () => {
        try {
          const token = localStorage.getItem('admin_token');
          await axios.delete(`${API_URL}/admin/horarios/${id}`, { headers: { Authorization: `Bearer ${token}` } });
          fetchData();
        } catch (err) {
          showToast('Erro ao remover horário', 'error');
        }
      }
    );
  };

  const diasSemana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];

  return (
    <div className="flex h-screen bg-[#0C0C12] text-gray-200 font-sans">

      {toast.show && (
        <div className={`fixed top-6 right-6 z-[200] flex items-center gap-4 px-6 py-4 rounded-2xl bg-[#151718] border shadow-2xl max-w-sm ${
          toast.type === 'success' ? 'border-green-500/50' :
          toast.type === 'error'   ? 'border-red-500/50'   :
                                     'border-amber-400/50'
        }`}>
          {toast.type === 'success' && <CheckCircle2 size={20} className="text-green-400 shrink-0" />}
          {toast.type === 'error'   && <X            size={20} className="text-red-400 shrink-0" />}
          {toast.type === 'warning' && <AlertTriangle size={20} className="text-amber-400 shrink-0" />}
          <p className="text-sm font-bold text-white flex-1">{toast.message}</p>
          <button onClick={() => setToast(t => ({ ...t, show: false }))} className="text-gray-500 hover:text-white transition-colors ml-2">
            <X size={16} />
          </button>
        </div>
      )}

      {confirmDialog.show && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[150] flex items-center justify-center p-6">
          <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-md w-full p-10">
            <div className="flex flex-col items-center text-center gap-6">
              <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center">
                <Trash2 size={28} className="text-red-500" />
              </div>
              <div>
                <h3 className="text-2xl font-black text-white mb-3">{confirmDialog.title}</h3>
                <p className="text-gray-400 font-medium whitespace-pre-line leading-relaxed">{confirmDialog.message}</p>
              </div>
              <div className="flex gap-4 w-full pt-2">
                <button
                  onClick={() => setConfirmDialog(d => ({ ...d, show: false }))}
                  className="flex-1 py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">
                  Cancelar
                </button>
                <button
                  onClick={() => {
                    const fn = confirmDialog.onConfirm;
                    setConfirmDialog(d => ({ ...d, show: false }));
                    fn?.();
                  }}
                  className="flex-1 py-4 rounded-2xl bg-red-500 font-black text-sm uppercase tracking-widest text-white hover:bg-red-400 transition-all shadow-2xl shadow-red-500/20">
                  Confirmar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar - Aumentada */}
      <aside className="w-80 bg-[#151718] border-r border-white/5 flex flex-col shadow-2xl">
        <div className="p-12">
          <div className="flex items-center gap-4">
             <div className="w-12 h-12 bg-[#4B39EF] rounded-2xl flex items-center justify-center font-black text-white text-2xl shadow-xl shadow-[#4B39EF]/30">S</div>
             <h1 className="text-2xl font-black text-white tracking-tighter">SCPI <span className="text-[#4B39EF]">CORE</span></h1>
          </div>
        </div>
        
        <nav className="flex-1 px-6 space-y-4">
          <SidebarItem icon={<LayoutDashboard size={24}/>} label="Turmas & Matrículas" active={activeTab === 'turmas'} onClick={() => setActiveTab('turmas')} />
          <SidebarItem icon={<Calendar size={24}/>} label="Grade Semanal" active={activeTab === 'horarios'} onClick={() => setActiveTab('horarios')} />
          <SidebarItem icon={<Users size={24}/>} label="Professores" active={activeTab === 'professores'} onClick={() => setActiveTab('professores')} />
          <SidebarItem icon={<GraduationCap size={24}/>} label="Alunos" active={activeTab === 'alunos'} onClick={() => setActiveTab('alunos')} />
          <SidebarItem icon={<FileText size={24}/>} label="Relatórios" active={activeTab === 'relatorios'} onClick={() => setActiveTab('relatorios')} />
        </nav>

        <div className="p-8 border-t border-white/5">
          <div className="flex items-center gap-4 p-5 bg-white/[0.03] rounded-[24px] mb-8">
             <div className="w-12 h-12 bg-gradient-to-tr from-[#4B39EF] to-[#5E47FF] rounded-full flex items-center justify-center font-bold text-white text-lg uppercase">{admin?.user_name.charAt(0)}</div>
             <div className="flex-1 overflow-hidden">
                <p className="text-sm font-black text-white truncate">{admin?.user_name}</p>
                <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">Administrador</p>
             </div>
          </div>
          <button onClick={onLogout} className="flex items-center gap-4 text-gray-500 hover:text-red-400 transition-all w-full px-4 py-4 font-black text-xs uppercase tracking-widest">
            <LogOut size={20}/> Sair do Sistema
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden bg-[#0C0C12] p-6 flex flex-col">
        {/* Renderiza Filtros de Turno e Semestre GLOBAIS para as abas Turmas e Horários */}
        {(activeTab === 'turmas' || activeTab === 'horarios' || activeTab === 'relatorios') && (
          <div className="w-full mb-4 flex-shrink-0">
            <div className="flex justify-between items-center mb-3">
               <div>
                  <h2 className="text-2xl font-black text-white tracking-tight">
                    {activeTab === 'turmas' ? 'Turmas' : activeTab === 'horarios' ? 'Grade Semanal' : 'Relatórios'}
                  </h2>
                  <p className="text-gray-500 text-sm mt-1 font-medium">
                    {activeTab === 'turmas' ? 'Gestão estratégica de disciplinas e alunos.' : activeTab === 'horarios' ? 'Visualize e organize o calendário acadêmico.' : 'Histórico imutável de todas as chamadas realizadas.'}
                  </p>
               </div>
               <div className="flex gap-4">
                  <div className="bg-[#151718] p-1.5 rounded-2xl border border-white/5 flex gap-1.5">
                     {['Matutino', 'Noturno'].map(t => (
                       <button
                         key={t}
                         onClick={() => { setFilterTurno(t); setTurmaPage(1); setRelatorioPage(1); }}
                         className={`px-6 py-2 rounded-xl text-xs font-black transition-all ${filterTurno === t ? 'bg-[#4B39EF] text-white shadow-lg' : 'text-gray-500 hover:text-white'}`}
                       >
                         {t.toUpperCase()}
                       </button>
                     ))}
                  </div>
               </div>
            </div>

            <div className="flex flex-wrap gap-2">
               {['Todos', '1', '2', '3', '4', '5', '6'].map(s => (
                 <button
                   key={s}
                   onClick={() => { setFilterSemestre(s); setTurmaPage(1); setRelatorioPage(1); }}
                   className={`px-4 py-1.5 rounded-full border text-xs font-black tracking-widest transition-all ${filterSemestre === s ? 'bg-white text-black border-white shadow-xl' : 'border-white/10 text-gray-500 hover:border-white/30'}`}
                 >
                   {s === 'Todos' ? 'TODOS' : `${s}º SEM`}
                 </button>
               ))}
            </div>
          </div>
        )}

        {activeTab === 'turmas' && (
          <div className="flex-1 overflow-hidden flex gap-6 min-h-0">
            {/* Form Lateral */}
            <div className="w-96 flex-shrink-0 flex flex-col">
               <div className="bg-[#151718] p-6 rounded-[32px] border border-white/5 shadow-2xl flex-1 flex flex-col">
                  <h3 className="text-base font-black text-white mb-4 flex items-center gap-2 flex-shrink-0"><Plus size={18} className="text-[#4B39EF]"/> NOVA TURMA</h3>
                  <form onSubmit={handleCreateTurma} className="flex-1 flex flex-col justify-between">
                     <InputGroup label="Nome da Disciplina">
                        <input className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Cálculo I" value={newTurma.nome_disciplina} onChange={e=>setNewTurma({...newTurma, nome_disciplina: e.target.value})} />
                     </InputGroup>
                     <div className="grid grid-cols-2 gap-3">
                        <InputGroup label="Código">
                           <input className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="MAT-01" value={newTurma.codigo_turma} onChange={e=>setNewTurma({...newTurma, codigo_turma: e.target.value})} />
                        </InputGroup>
                        <InputGroup label="Semestre">
                           <SelectInput value={newTurma.semestre} onChange={e=>setNewTurma({...newTurma, semestre: e.target.value})}>
                              {[1,2,3,4,5,6].map(v => <option key={v} value={v}>{v}º</option>)}
                           </SelectInput>
                        </InputGroup>
                     </div>
                     <InputGroup label="Turno">
                        <SearchableSelect
                          searchable={false}
                          value={newTurma.turno}
                          onChange={val => setNewTurma({...newTurma, turno: val})}
                          options={[{ value: 'Matutino', label: 'Matutino' }, { value: 'Noturno', label: 'Noturno' }]}
                          placeholder="Selecione o turno..."
                        />
                     </InputGroup>
                     <InputGroup label="Sala Padrão">
                        <input className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Lab 01" required value={newTurma.sala_padrao} onChange={e=>setNewTurma({...newTurma, sala_padrao: e.target.value})} />
                     </InputGroup>
                     <InputGroup label="Professor">
                        <SearchableSelect
                          value={newTurma.professor_id}
                          onChange={val => setNewTurma({...newTurma, professor_id: val})}
                          options={professores.map(p => ({ value: p.professor_id, label: p.nome }))}
                          placeholder="Selecione um professor..."
                        />
                     </InputGroup>
                     <button className="w-full bg-[#4B39EF] py-3 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">CADASTRAR TURMA</button>
                  </form>
               </div>
            </div>

            {/* Lista Principal */}
            <div className="flex-1 flex flex-col overflow-hidden min-h-0">
               <div className="relative mb-3 flex-shrink-0">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600" size={20} />
                  <input
                    className="w-full bg-[#151718] border border-white/5 rounded-2xl py-3 pl-12 pr-6 outline-none focus:ring-2 focus:ring-[#4B39EF]/30 transition-all font-bold text-sm"
                    placeholder="Pesquisar por disciplina ou código..."
                    value={searchTerm}
                    onChange={e => { setSearchSearchTerm(e.target.value); setTurmaPage(1); }}
                  />
               </div>

               <div className="flex-1 overflow-hidden flex flex-col gap-2 min-h-0">
                 {turmasPaged.map(t => (
                   <div key={t.turma_id} className="group bg-[#151718] hover:bg-[#1A1C1E] px-5 rounded-2xl border border-white/5 flex items-center justify-between transition-all hover:border-[#4B39EF]/40 flex-1 min-h-0">
                      <div className="flex items-center gap-4">
                         <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-lg flex-shrink-0 ${t.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                            {t.semestre}º
                         </div>
                         <div>
                            <div className="flex items-center gap-3">
                               <h4 className="font-black text-white text-base tracking-tight">{t.nome_disciplina}</h4>
                               <span className={`text-xs font-black px-2 py-0.5 rounded-md uppercase tracking-tighter ${t.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                                 {t.turno}
                               </span>
                            </div>
                            <p className="text-sm text-gray-500 font-bold mt-0.5 italic">Prof. {t.professor_nome} • <span className="text-gray-600">{t.codigo_turma}</span></p>
                         </div>
                      </div>
                      <div className="flex items-center gap-2">
                         <div className="text-right mr-4 hidden md:block">
                            <p className="text-base font-black text-white">{t.total_alunos}</p>
                            <p className="text-xs text-gray-600 font-black uppercase tracking-widest">Alunos</p>
                         </div>
                         <button onClick={() => openProfessorModal(t)} title="Atribuir professor" className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-amber-400 transition-all border border-white/5 hover:border-amber-400/30"><UserCog size={18}/></button>
                         <button onClick={() => openMatriculaModal(t)} title="Matricular aluno" className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-[#4B39EF] transition-all border border-white/5 hover:border-[#4B39EF]/30"><UserPlus size={18}/></button>
                         <label title="Importar CSV" className="cursor-pointer w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-[#22C55E] transition-all border border-white/5 hover:border-[#22C55E]/30"><Upload size={18}/><input type="file" accept=".csv" className="hidden" onChange={e => handleImportCSV(t.turma_id, e.target.files[0])} /></label>
                         <button onClick={() => handleDeleteTurma(t.turma_id)} title="Excluir turma" className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30"><Trash2 size={18}/></button>
                      </div>
                   </div>
                 ))}

                 {filteredTurmas.length === 0 && (
                   <div className="flex-1 flex flex-col items-center justify-center bg-white/[0.01] rounded-3xl border-2 border-dashed border-white/5">
                      <Filter className="text-gray-800 mb-4" size={48} />
                      <p className="text-gray-500 text-base font-black">Nenhuma turma para este filtro.</p>
                   </div>
                 )}
               </div>

               {turmasTotalPages > 1 && (
                 <div className="flex items-center justify-between pt-3 flex-shrink-0">
                   <p className="text-xs font-black text-gray-500">
                     {filteredTurmas.length} turma{filteredTurmas.length !== 1 ? 's' : ''} • página {turmaPage} de {turmasTotalPages}
                   </p>
                   <div className="flex gap-1.5">
                     <button onClick={() => setTurmaPage(p => Math.max(1, p - 1))} disabled={turmaPage === 1} className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed">
                       <ChevronDown size={14} className="rotate-90" />
                     </button>
                     {Array.from({ length: turmasTotalPages }, (_, i) => i + 1).map(p => (
                       <button key={p} onClick={() => setTurmaPage(p)} className={`w-8 h-8 rounded-xl text-xs font-black transition-all border ${turmaPage === p ? 'bg-[#4B39EF] text-white border-[#4B39EF] shadow-lg' : 'bg-white/5 border-white/10 text-gray-400 hover:text-white hover:bg-white/10'}`}>{p}</button>
                     ))}
                     <button onClick={() => setTurmaPage(p => Math.min(turmasTotalPages, p + 1))} disabled={turmaPage === turmasTotalPages} className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed">
                       <ChevronDown size={14} className="-rotate-90" />
                     </button>
                   </div>
                 </div>
               )}
            </div>
          </div>
        )}

        {activeTab === 'horarios' && (
          <div className="flex-1 overflow-hidden min-h-0">
            <div className="bg-[#151718] p-6 rounded-3xl border border-white/5 shadow-2xl shadow-black/40 h-full overflow-y-auto">
               <div className="grid grid-cols-5 gap-4">
                  {diasSemana.slice(0,5).map((dia, idx) => (
                    <div key={dia} className="space-y-3">
                      <div className="text-center font-black text-gray-600 text-xs uppercase tracking-[0.3em] mb-2">{dia}</div>
                      <div className="space-y-3">
                         {grade.filter(g => g.dia_semana === idx && g.turno === filterTurno && (filterSemestre === 'Todos' || g.semestre === filterSemestre)).sort((a,b) => a.inicio.localeCompare(b.inicio)).map(item => {
                           const isNight = item.turno === 'Noturno';
                           return (
                             <div key={item.horario_id} className={`p-4 rounded-2xl border-2 group transition-all ${isNight ? 'bg-indigo-500/5 border-indigo-500/10' : 'bg-amber-500/5 border-amber-500/10'}`}>
                                <p className={`text-[10px] font-black uppercase mb-1.5 ${isNight ? 'text-indigo-400' : 'text-amber-500'}`}>{item.inicio} — {item.fim}</p>
                                <p className="text-sm font-black text-white leading-tight mb-1.5">{item.nome_disciplina}</p>
                                <div className="flex items-center justify-between gap-2">
                                  <div className="flex items-center gap-1.5 opacity-40">
                                    <MapPin size={10} />
                                    <span className="text-[10px] font-black uppercase">{item.sala}</span>
                                  </div>
                                  <button
                                    onClick={() => handleDeleteHorario(item.horario_id)}
                                    className="w-7 h-7 rounded-lg bg-red-500/20 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all flex-shrink-0"
                                  >
                                    <Trash2 size={13} />
                                  </button>
                                </div>
                             </div>
                           );
                         })}
                         <button onClick={() => openHorarioModal(idx)} className="w-full py-4 border-2 border-dashed border-white/5 rounded-2xl flex items-center justify-center text-gray-700 hover:border-[#4B39EF]/40 hover:text-[#4B39EF] transition-all">
                            <Plus size={22} />
                         </button>
                      </div>
                    </div>
                  ))}
               </div>
            </div>
          </div>
        )}

        {horarioModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setHorarioModal(null)}>
            <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-2xl w-full p-10" onClick={e => e.stopPropagation()}>
              <div className="flex items-center gap-4 mb-8">
                <Clock className="text-[#4B39EF]" size={28} />
                <div>
                  <h3 className="text-2xl font-black text-white">Novo Horário</h3>
                  <p className="text-gray-500 text-sm font-bold mt-1">
                    {diasSemana[horarioModal.dia_semana]} • {filterTurno}
                  </p>
                </div>
              </div>
              <form onSubmit={handleAddHorario} className="space-y-6">
                <InputGroup label="Turma">
                  <SelectInput required value={horarioForm.turma_id} onChange={e => setHorarioForm({ ...horarioForm, turma_id: e.target.value })}>
                    <option value="">Selecione uma turma...</option>
                    {turmas.filter(t => t.turno === filterTurno).map(t => (
                      <option key={t.turma_id} value={t.turma_id}>{t.semestre}º • {t.nome_disciplina} ({t.codigo_turma})</option>
                    ))}
                  </SelectInput>
                </InputGroup>
                <div className="grid grid-cols-2 gap-6">
                  <InputGroup label="Slot Inicial">
                    <SelectInput value={horarioForm.slot_inicio} onChange={e => setHorarioForm({ ...horarioForm, slot_inicio: e.target.value, slot_fim: Math.max(Number(e.target.value), Number(horarioForm.slot_fim)) })}>
                      {getSlots(filterTurno).map(s => <option key={s.id} value={s.id}>{s.id}º — {s.inicio}</option>)}
                    </SelectInput>
                  </InputGroup>
                  <InputGroup label="Slot Final">
                    <SelectInput value={horarioForm.slot_fim} onChange={e => setHorarioForm({ ...horarioForm, slot_fim: e.target.value })}>
                      {getSlots(filterTurno).filter(s => s.id >= Number(horarioForm.slot_inicio)).map(s => <option key={s.id} value={s.id}>{s.id}º — {s.fim}</option>)}
                    </SelectInput>
                  </InputGroup>
                </div>
                <InputGroup label="Sala">
                  <input required className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all"
                    placeholder="Ex: Lab 01" value={horarioForm.sala} onChange={e => setHorarioForm({ ...horarioForm, sala: e.target.value })} />
                </InputGroup>
                <div className="flex gap-4 pt-4">
                  <button type="button" onClick={() => setHorarioModal(null)} className="flex-1 py-5 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">Cancelar</button>
                  <button type="submit" className="flex-1 bg-[#4B39EF] py-5 rounded-2xl font-black text-sm uppercase tracking-widest shadow-2xl shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">Adicionar</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {professorModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setProfessorModal(null)}>
            <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-xl w-full p-10" onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between mb-8">
                <div className="flex items-center gap-4">
                  <UserCog className="text-amber-400" size={28} />
                  <div>
                    <h3 className="text-2xl font-black text-white">Atribuir Professor</h3>
                    <p className="text-gray-500 text-sm font-bold mt-1">
                      {professorModal.nome_disciplina} • {professorModal.codigo_turma}
                    </p>
                  </div>
                </div>
                <button onClick={() => setProfessorModal(null)} className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all">
                  <X size={22} />
                </button>
              </div>

              <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
                <label className={`flex items-center gap-5 p-5 rounded-2xl border transition-all cursor-pointer ${selectedProfessorId === '' ? 'bg-amber-400/10 border-amber-400/40' : 'bg-white/[0.03] border-white/5 hover:border-white/20'}`}>
                  <input type="radio" name="professor" value="" checked={selectedProfessorId === ''} onChange={() => setSelectedProfessorId('')} className="w-5 h-5 accent-amber-400" />
                  <p className="font-black text-gray-400 italic">Sem professor</p>
                </label>
                {professores.map(p => (
                  <label key={p.professor_id} className={`flex items-center gap-5 p-5 rounded-2xl border transition-all cursor-pointer ${selectedProfessorId === p.professor_id ? 'bg-amber-400/10 border-amber-400/40' : 'bg-white/[0.03] border-white/5 hover:border-white/20'}`}>
                    <input type="radio" name="professor" value={p.professor_id} checked={selectedProfessorId === p.professor_id} onChange={() => setSelectedProfessorId(p.professor_id)} className="w-5 h-5 accent-amber-400" />
                    <div className="flex-1">
                      <p className="font-black text-white">{p.nome}</p>
                      <p className="text-xs text-gray-500 font-bold mt-1">{p.email}</p>
                    </div>
                  </label>
                ))}
              </div>

              <div className="flex gap-4 pt-8 border-t border-white/5 mt-6">
                <button type="button" onClick={() => setProfessorModal(null)} className="px-10 py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">Cancelar</button>
                <button type="button" onClick={handleAtribuirProfessor} className="flex-1 py-4 rounded-2xl bg-amber-400 font-black text-sm uppercase tracking-widest text-black hover:bg-amber-300 transition-all">Confirmar</button>
              </div>
            </div>
          </div>
        )}

        {matriculaModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setMatriculaModal(null)}>
            <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-3xl w-full p-10 max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between mb-8">
                <div className="flex items-center gap-4">
                  <UserPlus className="text-[#4B39EF]" size={28} />
                  <div>
                    <h3 className="text-2xl font-black text-white">Matricular Aluno</h3>
                    <p className="text-gray-500 text-sm font-bold mt-1">
                      {matriculaModal.nome_disciplina} • {matriculaModal.codigo_turma}
                    </p>
                  </div>
                </div>
                <button onClick={() => setMatriculaModal(null)} className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all">
                  <X size={22} />
                </button>
              </div>

              <div className="relative mb-6">
                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-600" size={20} />
                <input
                  className="w-full bg-black/40 border border-white/10 rounded-2xl py-4 pl-14 pr-6 outline-none focus:border-[#4B39EF] transition-all font-medium"
                  placeholder="Buscar por nome, email ou RA..."
                  value={searchAluno}
                  onChange={e => setSearchAluno(e.target.value)}
                />
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 -mx-2 px-2" style={{ minHeight: 200 }}>
                {loadingAlunos ? (
                  <div className="py-20 text-center text-gray-500 font-bold">Carregando alunos...</div>
                ) : (
                  (() => {
                    const q = searchAluno.toLowerCase();
                    const turmaTurno = matriculaModal?.turno;
                    const filtrados = alunosDisponiveis.filter(a =>
                      a.nome.toLowerCase().includes(q) ||
                      (a.email || '').toLowerCase().includes(q) ||
                      (a.ra || '').toLowerCase().includes(q)
                    );
                    if (filtrados.length === 0) {
                      return <div className="py-20 text-center text-gray-500 font-bold">Nenhum aluno encontrado.</div>;
                    }
                    return filtrados.map(a => {
                      const checked = selectedAlunoIds.has(a.aluno_id);
                      const turnoIncompativel = turmaTurno && a.turno && a.turno !== turmaTurno;
                      const disabled = a.ja_matriculado || turnoIncompativel;
                      return (
                        <label
                          key={a.aluno_id}
                          className={`flex items-center gap-5 p-5 rounded-2xl border transition-all ${
                            disabled
                              ? 'bg-white/[0.02] border-white/5 opacity-50 cursor-not-allowed'
                              : checked
                                ? 'bg-[#4B39EF]/10 border-[#4B39EF]/40 cursor-pointer'
                                : 'bg-white/[0.03] border-white/5 hover:border-white/20 cursor-pointer'
                          }`}
                        >
                          <input
                            type="checkbox"
                            disabled={disabled}
                            checked={checked || a.ja_matriculado}
                            onChange={() => !disabled && toggleAluno(a.aluno_id)}
                            className="w-5 h-5 accent-[#4B39EF] cursor-pointer disabled:cursor-not-allowed"
                          />
                          <div className="flex-1">
                            <p className="font-black text-white">{a.nome}</p>
                            <p className="text-xs text-gray-500 font-bold mt-1">
                              RA {a.ra || '—'} • {a.email}
                              {a.turno && <span className="ml-2 text-gray-600">• {a.turno}</span>}
                            </p>
                          </div>
                          {a.ja_matriculado && (
                            <span className="text-[10px] font-black uppercase tracking-widest text-[#22C55E] bg-[#22C55E]/10 px-3 py-1 rounded-lg">
                              Já matriculado
                            </span>
                          )}
                          {turnoIncompativel && (
                            <span className="text-[10px] font-black uppercase tracking-widest text-yellow-400 bg-yellow-400/10 px-3 py-1 rounded-lg">
                              Turno {a.turno}
                            </span>
                          )}
                        </label>
                      );
                    });
                  })()
                )}
              </div>

              <div className="flex gap-4 pt-8 border-t border-white/5 mt-6">
                <div className="flex-1 flex items-center text-gray-500 font-bold text-sm">
                  {selectedAlunoIds.size} selecionado(s)
                </div>
                <button type="button" onClick={() => setMatriculaModal(null)} className="px-10 py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">Cancelar</button>
                <button
                  type="button"
                  onClick={handleMatricular}
                  disabled={selectedAlunoIds.size === 0}
                  className="px-10 py-4 rounded-2xl bg-[#4B39EF] font-black text-sm uppercase tracking-widest text-white shadow-2xl shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  Matricular
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'professores' && (
          <div className="flex-1 overflow-hidden flex flex-col min-h-0">
            <h2 className="text-2xl font-black text-white tracking-tight mb-4 flex-shrink-0">Professores</h2>
            <div className="flex gap-6 flex-1 overflow-hidden min-h-0">
              <div className="w-96 flex-shrink-0">
                <div className="bg-[#151718] p-6 rounded-[32px] border border-white/5 shadow-2xl">
                  <h3 className="text-base font-black text-white mb-4 flex items-center gap-2"><Plus size={18} className="text-[#4B39EF]"/> NOVO PROFESSOR</h3>
                  <form onSubmit={handleCreateProfessor} className="space-y-4">
                    <InputGroup label="Nome Completo">
                      <input required minLength={3} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: João Silva" value={novoProfessor.nome} onChange={e=>setNovoProfessor({...novoProfessor, nome: e.target.value})} />
                    </InputGroup>
                    <InputGroup label="Email">
                      <input required type="email" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="professor@scpi.com" value={novoProfessor.email} onChange={e=>setNovoProfessor({...novoProfessor, email: e.target.value})} />
                    </InputGroup>
                    <InputGroup label="Departamento">
                      <input className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Informática" value={novoProfessor.departamento} onChange={e=>setNovoProfessor({...novoProfessor, departamento: e.target.value})} />
                    </InputGroup>
                    <button type="submit" className="w-full bg-[#4B39EF] py-3 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">CADASTRAR PROFESSOR</button>
                  </form>
                </div>
              </div>

              <div className="flex-1 overflow-hidden flex flex-col gap-3">
                <div className="bg-[#151718] rounded-3xl border border-white/5 overflow-hidden shadow-2xl flex-1">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                        <th className="px-5 py-4">Nome</th>
                        <th className="px-5 py-4">Departamento</th>
                        <th className="px-5 py-4">Email</th>
                        <th className="px-5 py-4">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {profPaged.map(p => (
                        <tr key={p.professor_id} className="hover:bg-white/[0.01] transition-colors group">
                          <td className="px-5 py-3">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 bg-gradient-to-br from-[#4B39EF] to-[#8E44AD] rounded-xl flex items-center justify-center font-black text-white text-sm shadow-lg shrink-0">{p.nome.charAt(0)}</div>
                              <p className="font-black text-white text-sm">{p.nome}</p>
                            </div>
                          </td>
                          <td className="px-5 py-3">
                            <div className="bg-white/5 inline-block px-3 py-1 rounded-lg text-xs font-black text-gray-400 border border-white/5 uppercase tracking-widest">{p.departamento || '—'}</div>
                          </td>
                          <td className="px-5 py-3 text-gray-300 font-bold text-sm">{p.email}</td>
                          <td className="px-5 py-3">
                            <button onClick={() => handleDeleteProfessor(p.professor_id, p.nome)} title="Excluir professor" className="w-9 h-9 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30"><Trash2 size={16} /></button>
                          </td>
                        </tr>
                      ))}
                      {professores.length === 0 && (
                        <tr><td colSpan="4" className="px-5 py-12 text-center text-gray-500 font-black">Nenhum professor cadastrado ainda.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                {profTotalPages > 1 && (
                  <div className="flex items-center justify-between flex-shrink-0">
                    <p className="text-xs font-black text-gray-500">{professores.length} professor{professores.length !== 1 ? 'es' : ''} • página {profPage} de {profTotalPages}</p>
                    <div className="flex gap-1.5">
                      <button onClick={() => setProfPage(p => Math.max(1, p - 1))} disabled={profPage === 1} className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"><ChevronDown size={14} className="rotate-90" /></button>
                      {Array.from({ length: profTotalPages }, (_, i) => i + 1).map(p => (
                        <button key={p} onClick={() => setProfPage(p)} className={`w-8 h-8 rounded-xl text-xs font-black transition-all border ${profPage === p ? 'bg-[#4B39EF] text-white border-[#4B39EF]' : 'bg-white/5 border-white/10 text-gray-400 hover:text-white hover:bg-white/10'}`}>{p}</button>
                      ))}
                      <button onClick={() => setProfPage(p => Math.min(profTotalPages, p + 1))} disabled={profPage === profTotalPages} className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"><ChevronDown size={14} className="-rotate-90" /></button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'alunos' && (
          <div className="flex-1 overflow-hidden flex flex-col min-h-0">
            <h2 className="text-2xl font-black text-white tracking-tight mb-4 flex-shrink-0">Alunos</h2>
            <div className="flex gap-6 flex-1 overflow-hidden min-h-0">
              <div className="w-96 flex-shrink-0">
                <div className="bg-[#151718] p-6 rounded-[32px] border border-white/5 shadow-2xl">
                  <h3 className="text-base font-black text-white mb-4 flex items-center gap-2"><Plus size={18} className="text-[#4B39EF]"/> NOVO ALUNO</h3>
                  <form onSubmit={handleCreateAluno} className="space-y-4">
                    <InputGroup label="Nome Completo">
                      <input required minLength={3} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Maria Souza" value={novoAluno.nome} onChange={e=>setNovoAluno({...novoAluno, nome: e.target.value})} />
                    </InputGroup>
                    <InputGroup label="Email">
                      <input required type="email" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="aluno@scpi.com" value={novoAluno.email} onChange={e=>setNovoAluno({...novoAluno, email: e.target.value})} />
                    </InputGroup>
                    <InputGroup label="RA">
                      <input required pattern="^[A-Za-z0-9]{4,20}$" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: 202400123" value={novoAluno.ra} onChange={e=>setNovoAluno({...novoAluno, ra: e.target.value})} />
                    </InputGroup>
                    <InputGroup label="Turno">
                      <SearchableSelect
                        searchable={false}
                        value={novoAluno.turno}
                        onChange={val => setNovoAluno({...novoAluno, turno: val})}
                        options={[{ value: 'Matutino', label: 'Matutino' }, { value: 'Noturno', label: 'Noturno' }]}
                        placeholder="Selecione o turno..."
                      />
                    </InputGroup>
                    <button type="submit" className="w-full bg-[#4B39EF] py-3 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">CADASTRAR ALUNO</button>
                  </form>
                </div>
              </div>

              <div className="flex-1 overflow-hidden flex flex-col gap-3">
                <div className="bg-[#151718] rounded-3xl border border-white/5 overflow-hidden shadow-2xl flex-1">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                        <th className="px-5 py-4">Nome</th>
                        <th className="px-5 py-4">Email</th>
                        <th className="px-5 py-4">RA</th>
                        <th className="px-5 py-4">Turno</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {alunosPaged.map(a => (
                        <tr key={a.aluno_id} className="hover:bg-white/[0.01] transition-colors">
                          <td className="px-5 py-3">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 bg-gradient-to-br from-[#22C55E] to-[#4B39EF] rounded-xl flex items-center justify-center font-black text-white text-sm shadow-lg shrink-0">{a.nome.charAt(0)}</div>
                              <p className="font-black text-white text-sm">{a.nome}</p>
                            </div>
                          </td>
                          <td className="px-5 py-3 text-gray-300 font-bold text-sm">{a.email}</td>
                          <td className="px-5 py-3">
                            <div className="bg-white/5 inline-block px-3 py-1 rounded-lg text-xs font-black text-gray-400 border border-white/5 uppercase tracking-widest">{a.ra || '—'}</div>
                          </td>
                          <td className="px-5 py-3">
                            {a.turno ? (
                              <span className={`text-xs font-black px-2 py-0.5 rounded-md uppercase tracking-tighter ${a.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>{a.turno}</span>
                            ) : (
                              <span className="text-xs text-gray-600 font-bold">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                      {alunos.length === 0 && (
                        <tr><td colSpan="4" className="px-5 py-12 text-center text-gray-500 font-black">Nenhum aluno cadastrado ainda.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                {alunoTotalPages > 1 && (
                  <div className="flex items-center justify-between flex-shrink-0">
                    <p className="text-xs font-black text-gray-500">{alunos.length} aluno{alunos.length !== 1 ? 's' : ''} • página {alunoPage} de {alunoTotalPages}</p>
                    <div className="flex gap-1.5">
                      <button onClick={() => setAlunoPage(p => Math.max(1, p - 1))} disabled={alunoPage === 1} className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"><ChevronDown size={14} className="rotate-90" /></button>
                      {Array.from({ length: alunoTotalPages }, (_, i) => i + 1).map(p => (
                        <button key={p} onClick={() => setAlunoPage(p)} className={`w-8 h-8 rounded-xl text-xs font-black transition-all border ${alunoPage === p ? 'bg-[#4B39EF] text-white border-[#4B39EF]' : 'bg-white/5 border-white/10 text-gray-400 hover:text-white hover:bg-white/10'}`}>{p}</button>
                      ))}
                      <button onClick={() => setAlunoPage(p => Math.min(alunoTotalPages, p + 1))} disabled={alunoPage === alunoTotalPages} className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"><ChevronDown size={14} className="-rotate-90" /></button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── ABA RELATÓRIOS ── */}
        {activeTab === 'relatorios' && (
          <div className="flex-1 overflow-hidden flex flex-col gap-3 min-h-0">
            {loadingRelatorios ? (
              <div className="flex-1 flex items-center justify-center">
                <p className="text-gray-500 font-black text-base">Carregando relatórios...</p>
              </div>
            ) : filteredRelatorios.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center bg-white/[0.01] rounded-3xl border-2 border-dashed border-white/5">
                <FileText className="text-gray-800 mb-4" size={48} />
                <p className="text-gray-500 text-base font-black">Nenhuma chamada para este filtro.</p>
              </div>
            ) : (
              <>
                <div className="flex-1 overflow-hidden flex flex-col gap-2 min-h-0">
                  {relatoriosPaged.map(r => (
                    <button
                      key={r.chamada_id}
                      onClick={() => handleOpenRelatorioDetalhe(r.chamada_id)}
                      className="group w-full bg-[#151718] hover:bg-[#1A1C1E] px-5 py-3 rounded-2xl border border-white/5 flex items-center justify-between transition-all hover:border-[#4B39EF]/30 text-left flex-shrink-0"
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-lg shrink-0 ${r.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                          {r.semestre}º
                        </div>
                        <div>
                          <div className="flex items-center gap-3 mb-0.5">
                            <h4 className="font-black text-white text-base tracking-tight">{r.nome_disciplina}</h4>
                            <span className={`text-xs font-black px-2 py-0.5 rounded-md uppercase tracking-tighter ${r.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>{r.turno}</span>
                          </div>
                          <p className="text-gray-500 font-bold text-xs">
                            Prof. {r.professor_nome} • {r.codigo_turma} • {r.data_chamada} • {r.horario_inicio} – {r.horario_fim}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6 shrink-0">
                        <div className="hidden md:flex items-center gap-4">
                          <div className="text-center"><p className="text-sm font-black text-white">{r.total_alunos}</p><p className="text-xs text-gray-600 font-black uppercase tracking-widest">Total</p></div>
                          <div className="text-center"><p className="text-sm font-black text-green-400">{r.presentes}</p><p className="text-xs text-gray-600 font-black uppercase tracking-widest">Pres.</p></div>
                          <div className="text-center"><p className="text-sm font-black text-red-400">{r.ausentes}</p><p className="text-xs text-gray-600 font-black uppercase tracking-widest">Aus.</p></div>
                        </div>
                        <div className="text-center min-w-[50px]">
                          <p className={`text-lg font-black ${r.percentual >= 75 ? 'text-green-400' : 'text-red-400'}`}>{r.percentual}%</p>
                          <p className="text-xs text-gray-600 font-black uppercase tracking-widest">Pres.</p>
                        </div>
                        <ChevronRight size={16} className="text-gray-600 group-hover:text-[#4B39EF] transition-colors" />
                      </div>
                    </button>
                  ))}
                </div>
                {relatorioTotalPages > 1 && (
                  <div className="flex items-center justify-between flex-shrink-0">
                    <p className="text-xs font-black text-gray-500">{filteredRelatorios.length} chamada{filteredRelatorios.length !== 1 ? 's' : ''} • página {relatorioPage} de {relatorioTotalPages}</p>
                    <div className="flex gap-1.5">
                      <button onClick={() => setRelatorioPage(p => Math.max(1, p - 1))} disabled={relatorioPage === 1} className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"><ChevronDown size={14} className="rotate-90" /></button>
                      {Array.from({ length: relatorioTotalPages }, (_, i) => i + 1).map(p => (
                        <button key={p} onClick={() => setRelatorioPage(p)} className={`w-8 h-8 rounded-xl text-xs font-black transition-all border ${relatorioPage === p ? 'bg-[#4B39EF] text-white border-[#4B39EF]' : 'bg-white/5 border-white/10 text-gray-400 hover:text-white hover:bg-white/10'}`}>{p}</button>
                      ))}
                      <button onClick={() => setRelatorioPage(p => Math.min(relatorioTotalPages, p + 1))} disabled={relatorioPage === relatorioTotalPages} className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"><ChevronDown size={14} className="-rotate-90" /></button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Modal detalhe de chamada */}
        {relatorioExpandido && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setRelatorioExpandido(null)}>
            <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-3xl w-full p-10 max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between mb-8">
                <div className="flex items-center gap-4">
                  <FileText className="text-[#4B39EF] shrink-0" size={28} />
                  <div>
                    <h3 className="text-2xl font-black text-white">{relatorioExpandido.nome_disciplina}</h3>
                    <p className="text-gray-500 text-sm font-bold mt-1">
                      {relatorioExpandido.data_chamada} • {relatorioExpandido.horario_inicio} – {relatorioExpandido.horario_fim} • Prof. {relatorioExpandido.professor_nome}
                    </p>
                  </div>
                </div>
                <button onClick={() => setRelatorioExpandido(null)} className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all shrink-0">
                  <X size={22} />
                </button>
              </div>

              <div className="grid grid-cols-4 gap-4 mb-8">
                {[
                  { label: 'Total', value: relatorioExpandido.total_alunos, cls: 'text-white', bg: 'bg-white/[0.03] border-white/5' },
                  { label: 'Presentes', value: relatorioExpandido.presentes, cls: 'text-green-400', bg: 'bg-green-500/5 border-green-500/10' },
                  { label: 'Ausentes', value: relatorioExpandido.ausentes, cls: 'text-red-400', bg: 'bg-red-500/5 border-red-500/10' },
                  {
                    label: 'Presença',
                    value: `${relatorioExpandido.percentual}%`,
                    cls: relatorioExpandido.percentual >= 75 ? 'text-green-400' : 'text-red-400',
                    bg: relatorioExpandido.percentual >= 75 ? 'bg-green-500/5 border-green-500/10' : 'bg-red-500/5 border-red-500/10',
                  },
                ].map(({ label, value, cls, bg }) => (
                  <div key={label} className={`${bg} rounded-2xl p-4 text-center border`}>
                    <p className={`text-2xl font-black ${cls}`}>{value}</p>
                    <p className="text-xs text-gray-500 font-black uppercase tracking-widest mt-1">{label}</p>
                  </div>
                ))}
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 -mx-2 px-2">
                {relatorioExpandido.alunos.map(a => (
                  <div key={a.aluno_id} className={`flex items-center gap-5 p-5 rounded-2xl border transition-all ${a.presente ? 'bg-green-500/[0.03] border-green-500/10' : 'bg-red-500/[0.03] border-red-500/10'}`}>
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-black text-lg shrink-0 ${a.presente ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                      {a.nome.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-black text-white truncate">{a.nome}</p>
                      <p className="text-xs text-gray-500 font-bold mt-1">RA {a.ra}</p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      {a.presente && a.tipo_registro !== '—' && (
                        <span className="text-[10px] font-black uppercase tracking-widest text-gray-500 bg-white/5 px-3 py-1 rounded-lg">
                          {a.tipo_registro}
                        </span>
                      )}
                      <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-lg ${a.presente ? 'text-green-400 bg-green-500/10' : 'text-red-400 bg-red-500/10'}`}>
                        {a.presente ? 'Presente' : 'Ausente'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-8 border-t border-white/5 mt-6">
                <button onClick={() => setRelatorioExpandido(null)} className="w-full py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">
                  Fechar
                </button>
              </div>
            </div>
          </div>
        )}

        {senhaTemporariaModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[150] flex items-center justify-center p-6">
            <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-md w-full p-10">
              <div className="flex flex-col items-center text-center gap-6">
                <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center">
                  <CheckCircle2 size={28} className="text-green-400" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-white mb-3">{senhaTemporariaModal.tipo} Criado!</h3>
                  <p className="text-gray-400 font-medium">{senhaTemporariaModal.nome} foi cadastrado com sucesso.</p>
                </div>
                <div className="w-full bg-black/40 rounded-2xl p-6 border border-white/10">
                  <p className="text-xs text-gray-500 font-black uppercase tracking-widest mb-3">Senha Temporária</p>
                  <p className="text-2xl font-black text-white tracking-widest font-mono">{senhaTemporariaModal.senha}</p>
                  <p className="text-xs text-gray-600 mt-3">Compartilhe com o usuário. Esta senha não será exibida novamente.</p>
                </div>
                <div className="flex gap-4 w-full">
                  <button
                    onClick={() => {navigator.clipboard?.writeText(senhaTemporariaModal.senha); showToast('Senha copiada!');}}
                    className="flex-1 py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">
                    Copiar Senha
                  </button>
                  <button
                    onClick={() => setSenhaTemporariaModal(null)}
                    className="flex-1 py-4 rounded-2xl bg-[#4B39EF] font-black text-sm uppercase tracking-widest text-white hover:bg-[#5E47FF] transition-all">
                    Fechar
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

function SidebarItem({ icon, label, active, onClick }) {
  return (
    <button 
      onClick={onClick} 
      className={`w-full flex items-center gap-5 px-8 py-5 rounded-[24px] transition-all duration-300 group ${
        active 
        ? 'bg-[#4B39EF] text-white shadow-2xl shadow-[#4B39EF]/40 scale-[1.03]' 
        : 'text-gray-500 hover:bg-white/5 hover:text-white'
      }`}
    >
      <div className={`${active ? 'text-white' : 'text-[#4B39EF] group-hover:text-white'} transition-colors`}>
         {icon}
      </div>
      <span className={`font-black text-xs uppercase tracking-[0.2em] ${active ? 'opacity-100' : 'opacity-70 group-hover:opacity-100'}`}>
        {label}
      </span>
    </button>
  );
}

function SelectInput({ children, className = '', ...props }) {
  return (
    <div className="relative">
      <select
        style={{ colorScheme: 'dark' }}
        className={`w-full bg-[#1A1C1E] border border-white/10 rounded-xl px-4 py-3 pr-10 text-sm text-white outline-none focus:border-[#4B39EF] focus:ring-2 focus:ring-[#4B39EF]/20 transition-all appearance-none cursor-pointer ${className}`}
        {...props}
      >
        {children}
      </select>
      <ChevronDown size={18} className="absolute right-5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
    </div>
  );
}

function InputGroup({ label, children }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-black text-gray-400 uppercase tracking-[0.15em] ml-1">{label}</label>
      {children}
    </div>
  );
}

function SearchableSelect({ value, onChange, options, placeholder = 'Selecione...', searchable = true, className = '' }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [openUp, setOpenUp] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleOpen = () => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      setOpenUp(spaceBelow < 220);
    }
    setOpen(o => !o);
    setSearch('');
  };

  const filtered = options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()));
  const selected = options.find(o => o.value === value);

  const handleSelect = (opt) => {
    onChange(opt.value);
    setSearch('');
    setOpen(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange('');
    setSearch('');
  };

  return (
    <div ref={ref} className={`relative ${className}`}>
      <div
        onClick={handleOpen}
        className="w-full bg-[#1A1C1E] border border-white/10 rounded-xl px-4 py-3 pr-10 text-sm text-white outline-none focus:border-[#4B39EF] transition-all cursor-pointer flex items-center justify-between gap-2 select-none"
        style={{ minHeight: '46px' }}
      >
        <span className={selected ? 'text-white' : 'text-gray-600'}>
          {selected ? selected.label : placeholder}
        </span>
        <div className="flex items-center gap-1 flex-shrink-0">
          {selected && (
            <button
              type="button"
              onClick={handleClear}
              className="w-5 h-5 flex items-center justify-center text-gray-500 hover:text-white transition-colors"
            >
              <X size={12} />
            </button>
          )}
          <ChevronDown size={14} className={`text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {open && (
        <div className={`absolute z-50 w-full bg-[#1A1C1E] border border-white/10 rounded-xl shadow-2xl overflow-hidden ${openUp ? 'bottom-full mb-1.5' : 'top-full mt-1.5'}`}>
          {searchable && (
            <div className="p-2 border-b border-white/5">
              <div className="relative">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  autoFocus
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Pesquisar..."
                  className="w-full bg-black/30 rounded-lg pl-8 pr-3 py-2 text-sm text-white outline-none placeholder:text-gray-600 border border-white/5 focus:border-[#4B39EF] transition-all"
                  onClick={e => e.stopPropagation()}
                />
              </div>
            </div>
          )}
          <div className="max-h-48 overflow-y-auto">
            <div
              onClick={() => handleSelect({ value: '', label: placeholder })}
              className="px-4 py-2.5 text-sm text-gray-500 hover:bg-white/5 cursor-pointer italic transition-colors"
            >
              {placeholder}
            </div>
            {filtered.length === 0 ? (
              <div className="px-4 py-3 text-sm text-gray-600 text-center">Nenhum resultado</div>
            ) : (
              filtered.map(opt => (
                <div
                  key={opt.value}
                  onClick={() => handleSelect(opt)}
                  className={`px-4 py-2.5 text-sm cursor-pointer transition-colors ${opt.value === value ? 'bg-[#4B39EF]/20 text-[#7B6EFF] font-black' : 'text-white hover:bg-white/5'}`}
                >
                  {opt.label}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
