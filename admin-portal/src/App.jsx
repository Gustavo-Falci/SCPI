import React, { useState, useEffect } from 'react';
import {
  Users, BookOpen, Calendar, Plus, Trash2, ChevronRight, ChevronDown, LogOut,
  LayoutDashboard, Clock, MapPin, Upload, FileText, CheckCircle2, Lock,
  Filter, Sun, Moon, GraduationCap, Search, UserPlus, X, UserCog, AlertTriangle
} from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://192.168.5.129:8000';

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

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (token) {
       setIsLoggedIn(true);
       setAdminUser(JSON.parse(localStorage.getItem('admin_user')));
    }
  }, []);

  if (!isLoggedIn) {
    return <LoginScreen onLogin={(data) => {
      localStorage.setItem('admin_token', data.access_token);
      localStorage.setItem('admin_user', JSON.stringify(data));
      setAdminUser(data);
      setIsLoggedIn(true);
    }} />;
  }

  return <AdminDashboard admin={adminUser} onLogout={() => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    setIsLoggedIn(false);
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

  const [newTurma, setNewTurma] = useState({ professor_id: '', codigo_turma: '', nome_disciplina: '', periodo_letivo: '2025-1', sala_padrao: '', turno: 'Matutino', semestre: '1' });

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
      setNewTurma({ ...newTurma, nome_disciplina: '', codigo_turma: '' });
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

  const handleDeleteHorario = async (id) => {
    try {
      const token = localStorage.getItem('admin_token');
      await axios.delete(`${API_URL}/admin/horarios/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      fetchData();
    } catch (err) {
      showToast('Erro ao remover horário', 'error');
    }
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

      <main className="flex-1 overflow-y-auto bg-[#0C0C12] p-16">
        {/* Renderiza Filtros de Turno e Semestre GLOBAIS para as abas Turmas e Horários */}
        {(activeTab === 'turmas' || activeTab === 'horarios') && (
          <div className="max-w-7xl mx-auto mb-12">
            <div className="flex justify-between items-end mb-8">
               <div>
                  <h2 className="text-5xl font-black text-white tracking-tight">
                    {activeTab === 'turmas' ? 'Turmas' : 'Grade Semanal'}
                  </h2>
                  <p className="text-gray-500 text-xl mt-4 font-medium">
                    {activeTab === 'turmas' ? 'Gestão estratégica de disciplinas e alunos.' : 'Visualize e organize o calendário acadêmico.'}
                  </p>
               </div>
               <div className="flex gap-4">
                  <div className="bg-[#151718] p-2 rounded-[24px] border border-white/5 flex gap-2">
                     {['Matutino', 'Noturno'].map(t => (
                       <button 
                         key={t}
                         onClick={() => setFilterTurno(t)}
                         className={`px-10 py-4 rounded-2xl text-sm font-black transition-all ${filterTurno === t ? 'bg-[#4B39EF] text-white shadow-2xl' : 'text-gray-500 hover:text-white'}`}
                       >
                         {t.toUpperCase()}
                       </button>
                     ))}
                  </div>
               </div>
            </div>

            {/* Filtros de Semestre */}
            <div className="flex flex-wrap gap-4">
               {['Todos', '1', '2', '3', '4', '5', '6'].map(s => (
                 <button 
                   key={s} 
                   onClick={() => setFilterSemestre(s)}
                   className={`px-8 py-4 rounded-full border text-xs font-black tracking-widest transition-all ${filterSemestre === s ? 'bg-white text-black border-white shadow-xl' : 'border-white/10 text-gray-500 hover:border-white/30'}`}
                 >
                   {s === 'Todos' ? 'TODOS OS SEMESTRES' : `${s}º SEMESTRE`}
                 </button>
               ))}
            </div>
          </div>
        )}

        {activeTab === 'turmas' && (
          <div className="max-w-7xl mx-auto space-y-16">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-16">
              {/* Form Lateral - Robusto */}
              <div className="lg:col-span-4 space-y-8">
                 <div className="bg-[#151718] p-10 rounded-[40px] border border-white/5 shadow-2xl">
                    <h3 className="text-xl font-black text-white mb-10 flex items-center gap-3"><Plus size={24} className="text-[#4B39EF]"/> NOVA TURMA</h3>
                    <form onSubmit={handleCreateTurma} className="space-y-8">
                       <InputGroup label="Nome da Disciplina">
                          <input className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Cálculo I" value={newTurma.nome_disciplina} onChange={e=>setNewTurma({...newTurma, nome_disciplina: e.target.value})} />
                       </InputGroup>
                       <div className="grid grid-cols-2 gap-6">
                          <InputGroup label="Código">
                             <input className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all" placeholder="MAT-01" value={newTurma.codigo_turma} onChange={e=>setNewTurma({...newTurma, codigo_turma: e.target.value})} />
                          </InputGroup>
                          <InputGroup label="Semestre">
                             <select className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all appearance-none cursor-pointer" value={newTurma.semestre} onChange={e=>setNewTurma({...newTurma, semestre: e.target.value})}>
                                {[1,2,3,4,5,6].map(v => <option key={v} value={v}>{v}º</option>)}
                             </select>
                          </InputGroup>
                       </div>
                       <InputGroup label="Turno">
                          <select className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all appearance-none cursor-pointer" value={newTurma.turno} onChange={e=>setNewTurma({...newTurma, turno: e.target.value})}>
                             <option value="Matutino">Matutino</option>
                             <option value="Noturno">Noturno</option>
                          </select>
                       </InputGroup>
                       <InputGroup label="Professor">
                          <select className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all appearance-none cursor-pointer" value={newTurma.professor_id} onChange={e=>setNewTurma({...newTurma, professor_id: e.target.value})}>
                             <option value="">Selecione...</option>
                             {professores.map(p => <option key={p.professor_id} value={p.professor_id}>{p.nome}</option>)}
                          </select>
                       </InputGroup>
                       <button className="w-full bg-[#4B39EF] py-6 rounded-2xl font-black text-sm uppercase tracking-widest shadow-2xl shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">CADASTRAR TURMA</button>
                    </form>
                 </div>
              </div>

              {/* Lista Principal - Wide */}
              <div className="lg:col-span-8 space-y-6">
                 <div className="relative mb-12">
                    <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-gray-600" size={28} />
                    <input 
                      className="w-full bg-[#151718] border border-white/5 rounded-[30px] py-6 pl-16 pr-8 outline-none focus:ring-2 focus:ring-[#4B39EF]/30 transition-all font-bold text-lg"
                      placeholder="Pesquisar por disciplina ou código..."
                      value={searchTerm}
                      onChange={e => setSearchSearchTerm(e.target.value)}
                    />
                 </div>

                 {filteredTurmas.map(t => (
                   <div key={t.turma_id} className="group bg-[#151718] hover:bg-[#1A1C1E] p-8 rounded-[40px] border border-white/5 flex items-center justify-between transition-all hover:border-[#4B39EF]/40 shadow-lg">
                      <div className="flex items-center gap-8">
                         <div className={`w-20 h-20 rounded-3xl flex items-center justify-center font-black text-3xl ${t.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                            {t.semestre}º
                         </div>
                         <div>
                            <div className="flex items-center gap-4">
                               <h4 className="font-black text-white text-2xl tracking-tight">{t.nome_disciplina}</h4>
                               <span className={`text-xs font-black px-3 py-1 rounded-lg uppercase tracking-tighter ${t.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                                 {t.turno}
                               </span>
                            </div>
                            <p className="text-lg text-gray-500 font-bold mt-2 italic">Prof. {t.professor_nome} • <span className="text-gray-600">{t.codigo_turma}</span></p>
                         </div>
                      </div>
                      <div className="flex items-center gap-4">
                         <div className="text-right mr-6 hidden md:block">
                            <p className="text-xl font-black text-white">{t.total_alunos}</p>
                            <p className="text-xs text-gray-600 font-black uppercase tracking-widest">Alunos</p>
                         </div>
                         <button
                            onClick={() => openProfessorModal(t)}
                            title="Atribuir professor"
                            className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center text-gray-500 hover:text-amber-400 transition-all border border-white/5 hover:border-amber-400/30">
                           <UserCog size={24}/>
                         </button>
                         <button
                            onClick={() => openMatriculaModal(t)}
                            title="Matricular aluno individualmente"
                            className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center text-gray-500 hover:text-[#4B39EF] transition-all border border-white/5 hover:border-[#4B39EF]/30">
                           <UserPlus size={24}/>
                         </button>
                         <label
                            title="Importar alunos via CSV"
                            className="cursor-pointer w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center text-gray-500 hover:text-[#22C55E] transition-all border border-white/5 hover:border-[#22C55E]/30">
                           <Upload size={24}/>
                           <input type="file" accept=".csv" className="hidden" onChange={e => handleImportCSV(t.turma_id, e.target.files[0])} />
                         </label>
                         <button onClick={() => handleDeleteTurma(t.turma_id)} title="Excluir turma" className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30"><Trash2 size={24}/></button>
                      </div>
                   </div>
                 ))}
                 
                 {filteredTurmas.length === 0 && (
                   <div className="py-32 text-center bg-white/[0.01] rounded-[50px] border-2 border-dashed border-white/5">
                      <Filter className="mx-auto text-gray-800 mb-6" size={64} />
                      <p className="text-gray-500 text-xl font-black">Nenhuma turma para este filtro.</p>
                   </div>
                 )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'horarios' && (
          <div className="max-w-7xl mx-auto space-y-16">
            <div className="bg-[#151718] p-12 rounded-[60px] border border-white/5 shadow-2xl shadow-black/40">
               <div className="grid grid-cols-5 gap-10">
                  {diasSemana.slice(0,5).map((dia, idx) => (
                    <div key={dia} className="space-y-8">
                      <div className="text-center font-black text-gray-600 text-xs uppercase tracking-[0.4em] mb-4">{dia}</div>
                      <div className="space-y-6">
                         {grade.filter(g => g.dia_semana === idx && g.turno === filterTurno && (filterSemestre === 'Todos' || g.semestre === filterSemestre)).sort((a,b) => a.inicio.localeCompare(b.inicio)).map(item => {
                           const isNight = item.turno === 'Noturno';
                           return (
                             <div key={item.horario_id} className={`p-6 rounded-[32px] border-2 shadow-2xl relative group transition-all hover:scale-[1.05] ${isNight ? 'bg-indigo-500/5 border-indigo-500/10' : 'bg-amber-500/5 border-amber-500/10'}`}>
                                <p className={`text-[11px] font-black uppercase mb-3 ${isNight ? 'text-indigo-400' : 'text-amber-500'}`}>{item.inicio} — {item.fim}</p>
                                <p className="text-md font-black text-white leading-tight mb-3">{item.nome_disciplina}</p>
                                <div className="flex items-center gap-2 opacity-40">
                                   <MapPin size={12} />
                                   <span className="text-[11px] font-black uppercase">{item.sala}</span>
                                </div>
                                <button onClick={() => handleDeleteHorario(item.horario_id)} className="absolute -top-3 -right-3 w-10 h-10 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all shadow-2xl scale-0 group-hover:scale-100 active:scale-90">
                                   <Trash2 size={18} />
                                </button>
                             </div>
                           );
                         })}
                         <button onClick={() => openHorarioModal(idx)} className="w-full py-8 border-2 border-dashed border-white/5 rounded-[32px] flex items-center justify-center text-gray-700 hover:border-[#4B39EF]/40 hover:text-[#4B39EF] transition-all">
                            <Plus size={32} />
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
                  <select required className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all appearance-none cursor-pointer"
                    value={horarioForm.turma_id} onChange={e => setHorarioForm({ ...horarioForm, turma_id: e.target.value })}>
                    <option value="">Selecione uma turma...</option>
                    {turmas.filter(t => t.turno === filterTurno).map(t => (
                      <option key={t.turma_id} value={t.turma_id}>{t.semestre}º • {t.nome_disciplina} ({t.codigo_turma})</option>
                    ))}
                  </select>
                </InputGroup>
                <div className="grid grid-cols-2 gap-6">
                  <InputGroup label="Slot Inicial">
                    <select className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all appearance-none cursor-pointer"
                      value={horarioForm.slot_inicio} onChange={e => setHorarioForm({ ...horarioForm, slot_inicio: e.target.value, slot_fim: Math.max(Number(e.target.value), Number(horarioForm.slot_fim)) })}>
                      {getSlots(filterTurno).map(s => <option key={s.id} value={s.id}>{s.id}º — {s.inicio}</option>)}
                    </select>
                  </InputGroup>
                  <InputGroup label="Slot Final">
                    <select className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all appearance-none cursor-pointer"
                      value={horarioForm.slot_fim} onChange={e => setHorarioForm({ ...horarioForm, slot_fim: e.target.value })}>
                      {getSlots(filterTurno).filter(s => s.id >= Number(horarioForm.slot_inicio)).map(s => <option key={s.id} value={s.id}>{s.id}º — {s.fim}</option>)}
                    </select>
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
          <div className="max-w-7xl mx-auto space-y-12">
            <h2 className="text-5xl font-black text-white tracking-tight">Professores</h2>
            <div className="bg-[#151718] rounded-[50px] border border-white/5 overflow-hidden shadow-2xl">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                    <th className="px-12 py-10">Membro do Corpo Docente</th>
                    <th className="px-12 py-10">Departamento</th>
                    <th className="px-12 py-10">Contato Oficial</th>
                    <th className="px-12 py-10">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {professores.map(p => (
                    <tr key={p.professor_id} className="hover:bg-white/[0.01] transition-colors group">
                      <td className="px-12 py-12">
                        <div className="flex items-center gap-6">
                          <div className="w-16 h-16 bg-gradient-to-br from-[#4B39EF] to-[#8E44AD] rounded-2xl flex items-center justify-center font-black text-white text-2xl shadow-xl">{p.nome.charAt(0)}</div>
                          <div>
                             <p className="font-black text-white text-xl">{p.nome}</p>
                             <p className="text-sm text-[#4B39EF] font-black uppercase tracking-[0.2em] mt-2">Doutorado / Mestre</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-12 py-12">
                         <div className="bg-white/5 inline-block px-6 py-3 rounded-2xl text-sm font-black text-gray-400 border border-white/5 uppercase tracking-widest">{p.departamento}</div>
                      </td>
                      <td className="px-12 py-12 text-gray-300 font-bold text-lg">{p.email}</td>
                      <td className="px-12 py-12">
                        <button
                          onClick={() => handleDeleteProfessor(p.professor_id, p.nome)}
                          title="Excluir professor"
                          className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30"
                        >
                          <Trash2 size={24} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
        className={`w-full bg-[#1A1C1E] border border-white/10 rounded-2xl px-6 py-5 pr-14 text-lg text-white outline-none focus:border-[#4B39EF] focus:ring-2 focus:ring-[#4B39EF]/20 transition-all appearance-none cursor-pointer ${className}`}
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
    <div className="space-y-4">
      <label className="text-xs font-black text-gray-400 uppercase tracking-[0.2em] ml-1">{label}</label>
      {children}
    </div>
  );
}
