import React, { useState, useEffect } from 'react';
import { 
  Users, BookOpen, Calendar, Plus, Trash2, ChevronRight, LogOut,
  LayoutDashboard, Clock, MapPin, Upload, FileText, CheckCircle2, Lock
} from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://192.168.5.108:8000';


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

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Usando URLSearchParams para garantir o formato x-www-form-urlencoded exigido pelo FastAPI
      const params = new URLSearchParams();
      params.append('username', email.trim());
      params.append('password', password);
      
      const res = await axios.post(`${API_URL}/auth/login`, params.toString(), {
        headers: { 
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        }
      });
      onLogin(res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : "Erro de conexão ou credenciais");
      alert(`Falha no login: ${msg}`);
      console.error("Erro detalhado:", err.response || err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0C0C12] p-4">
      <div className="w-full max-w-md bg-[#151718] rounded-3xl p-8 border border-white/5 shadow-2xl">
        <div className="text-center mb-10">
          <div className="w-16 h-16 bg-[#4B39EF]/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Lock className="text-[#4B39EF]" size={32} />
          </div>
          <h1 className="text-2xl font-bold text-white">Portal Admin</h1>
          <p className="text-gray-400 text-sm mt-2">Acesse as ferramentas de gestão do SCPI</p>
        </div>
        
        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-widest ml-1">E-mail</label>
            <input 
              type="email" required
              className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 focus:border-[#4B39EF] outline-none transition-all"
              placeholder="admin@scpi.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-widest ml-1">Senha</label>
            <input 
              type="password" required
              className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 focus:border-[#4B39EF] outline-none transition-all"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
          </div>
          <button 
            disabled={loading}
            className="w-full bg-[#4B39EF] hover:bg-[#5E47FF] text-white font-bold py-4 rounded-xl shadow-lg transition-all"
          >
            {loading ? 'AUTENTICANDO...' : 'ENTRAR NO PAINEL'}
          </button>
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

  const [newTurma, setNewTurma] = useState({ professor_id: '', codigo_turma: '', nome_disciplina: '', periodo_letivo: '2025-1', sala_padrao: '' });
  const [newHorario, setNewHorario] = useState({ turma_id: '', dia_semana: 0, horario_inicio: '08:00', horario_fim: '10:00', sala: '' });

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

  const handleImportCSV = async (turmaId, file) => {
    if(!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const token = localStorage.getItem('admin_token');
      const res = await axios.post(`${API_URL}/admin/turmas/${turmaId}/importar-alunos`, formData, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'multipart/form-data' }
      });
      alert(res.data.mensagem);
      fetchData();
    } catch (err) {
      alert("Erro na importação");
    }
  };

  const handleAddHorario = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('admin_token');
      await axios.post(`${API_URL}/admin/horarios`, newHorario, { headers: { Authorization: `Bearer ${token}` } });
      alert("Horário adicionado!");
      fetchData();
    } catch (err) {
      alert("Erro ao adicionar horário");
    }
  };

  const handleDeleteHorario = async (id) => {
    try {
      const token = localStorage.getItem('admin_token');
      await axios.delete(`${API_URL}/admin/horarios/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      fetchData();
    } catch (err) {
      alert("Erro ao remover");
    }
  };

  const diasSemana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];

  return (
    <div className="flex h-screen bg-[#0C0C12] text-gray-200">
      <aside className="w-64 bg-[#151718] border-r border-white/10 flex flex-col">
        <div className="p-8">
          <h1 className="text-2xl font-bold text-[#4B39EF]">SCPI <span className="text-white text-xs font-normal block opacity-50 uppercase tracking-tighter">Administration</span></h1>
        </div>
        <nav className="flex-1 px-4 space-y-2">
          <SidebarItem icon={<LayoutDashboard size={18}/>} label="Turmas" active={activeTab === 'turmas'} onClick={() => setActiveTab('turmas')} />
          <SidebarItem icon={<Calendar size={18}/>} label="Grade Horária" active={activeTab === 'horarios'} onClick={() => setActiveTab('horarios')} />
          <SidebarItem icon={<Users size={18}/>} label="Professores" active={activeTab === 'professores'} onClick={() => setActiveTab('professores')} />
        </nav>
        <div className="p-4 border-t border-white/10">
          <div className="px-4 py-3 mb-4 bg-white/5 rounded-xl border border-white/5">
            <p className="text-xs text-gray-500 uppercase font-bold">Logado como</p>
            <p className="text-sm font-bold text-white truncate">{admin?.user_name}</p>
          </div>
          <button onClick={onLogout} className="flex items-center gap-3 text-gray-400 hover:text-red-400 transition-colors w-full px-4 py-2">
            <LogOut size={18}/> <span>Sair do Sistema</span>
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-10">
        {activeTab === 'turmas' && (
          <div className="space-y-8">
            <div className="flex justify-between items-end">
              <div>
                <h2 className="text-3xl font-bold text-white tracking-tight">Gestão de Turmas</h2>
                <p className="text-gray-400 mt-2">Crie disciplinas e gerencie matriculados via CSV.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
              <div className="xl:col-span-1 bg-[#1A1C1E] p-8 rounded-3xl border border-white/5 shadow-xl">
                <h3 className="text-lg font-bold mb-6 flex items-center gap-2">Nova Disciplina</h3>
                <form onSubmit={e => { e.preventDefault(); /* chama handleCreateTurma */ }} className="space-y-5">
                   <InputGroup label="Nome">
                      <input className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 outline-none" value={newTurma.nome_disciplina} onChange={e=>setNewTurma({...newTurma, nome_disciplina: e.target.value})} />
                   </InputGroup>
                   <div className="grid grid-cols-2 gap-4">
                     <InputGroup label="Código">
                        <input className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 outline-none" value={newTurma.codigo_turma} onChange={e=>setNewTurma({...newTurma, codigo_turma: e.target.value})} />
                     </InputGroup>
                     <InputGroup label="Sala">
                        <input className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 outline-none" value={newTurma.sala_padrao} onChange={e=>setNewTurma({...newTurma, sala_padrao: e.target.value})} />
                     </InputGroup>
                   </div>
                   <InputGroup label="Professor">
                      <select className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 outline-none" value={newTurma.professor_id} onChange={e=>setNewTurma({...newTurma, professor_id: e.target.value})}>
                        <option value="">Selecione...</option>
                        {professores.map(p => <option key={p.professor_id} value={p.professor_id}>{p.nome}</option>)}
                      </select>
                   </InputGroup>
                   <button className="w-full bg-[#4B39EF] py-4 rounded-xl font-bold">CRIAR TURMA</button>
                </form>
              </div>

              <div className="xl:col-span-2 space-y-4">
                {turmas.map(t => (
                  <div key={t.turma_id} className="bg-[#1A1C1E] p-6 rounded-3xl border border-white/5 flex items-center justify-between group">
                    <div className="flex items-center gap-5">
                      <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-[#4B39EF]"><BookOpen size={24}/></div>
                      <div>
                        <h4 className="font-bold text-white text-lg">{t.nome_disciplina}</h4>
                        <p className="text-sm text-gray-500">Prof. {t.professor_nome} • {t.total_alunos} alunos</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 cursor-pointer bg-white/5 px-4 py-2 rounded-xl hover:bg-white/10 transition-all border border-white/5">
                        <Upload size={16} className="text-[#22C55E]"/>
                        <span className="text-xs font-bold uppercase tracking-wider">CSV</span>
                        <input type="file" accept=".csv" className="hidden" onChange={e => handleImportCSV(t.turma_id, e.target.files[0])} />
                      </label>
                      <button onClick={() => {}} className="p-3 text-gray-500 hover:text-red-400 transition-all"><Trash2 size={20}/></button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'horarios' && (
          <div className="space-y-8">
            <h2 className="text-3xl font-bold text-white tracking-tight">Grade de Aulas</h2>
            
            <div className="bg-[#1A1C1E] p-8 rounded-[40px] border border-white/5">
               {/* Grade Visual */}
               <div className="grid grid-cols-7 gap-6">
                  {diasSemana.map((dia, idx) => (
                    <div key={dia} className="space-y-4">
                      <div className="text-center font-bold text-gray-500 text-xs uppercase tracking-[0.2em]">{dia.substring(0,3)}</div>
                      <div className="min-h-[500px] bg-black/20 rounded-3xl border border-white/5 p-3 space-y-3">
                         {grade.filter(g => g.dia_semana === idx).map(item => (
                           <div key={item.horario_id} className="bg-[#151718] p-4 rounded-2xl border-l-4 border-[#4B39EF] shadow-lg relative group">
                              <p className="text-[10px] font-bold text-[#4B39EF] uppercase">{item.inicio} - {item.fim}</p>
                              <p className="text-xs font-bold text-white mt-1 leading-tight">{item.nome_disciplina}</p>
                              <p className="text-[10px] text-gray-500 mt-1 flex items-center gap-1"><MapPin size={10}/> {item.sala}</p>
                              <button onClick={() => handleDeleteHorario(item.horario_id)} className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-all text-red-500/50 hover:text-red-500">
                                <Trash2 size={12}/>
                              </button>
                           </div>
                         ))}
                         
                         {/* Drop Target Simulado */}
                         <button 
                           onClick={() => setNewHorario({...newHorario, dia_semana: idx})}
                           className="w-full py-4 border-2 border-dashed border-white/5 rounded-2xl flex items-center justify-center text-gray-600 hover:border-[#4B39EF]/30 hover:text-[#4B39EF] transition-all"
                         >
                           <Plus size={16}/>
                         </button>
                      </div>
                    </div>
                  ))}
               </div>
            </div>

            {/* Modal/Overlay de Adição Simples */}
            <div className="bg-[#1A1C1E] p-8 rounded-3xl border border-white/5 mt-8">
               <h3 className="font-bold mb-6">Agendar Novo Horário</h3>
               <form onSubmit={handleAddHorario} className="flex flex-wrap gap-6 items-end">
                  <InputGroup label="Turma">
                    <select className="bg-black/20 border border-white/10 rounded-xl px-4 py-3 outline-none w-64" value={newHorario.turma_id} onChange={e=>setNewHorario({...newHorario, turma_id: e.target.value})}>
                       <option value="">Selecione...</option>
                       {turmas.map(t => <option key={t.turma_id} value={t.turma_id}>{t.nome_disciplina}</option>)}
                    </select>
                  </InputGroup>
                  <InputGroup label="Dia">
                    <select className="bg-black/20 border border-white/10 rounded-xl px-4 py-3 outline-none w-40" value={newHorario.dia_semana} onChange={e=>setNewHorario({...newHorario, dia_semana: parseInt(e.target.value)})}>
                       {diasSemana.map((d, i) => <option key={i} value={i}>{d}</option>)}
                    </select>
                  </InputGroup>
                  <div className="flex gap-4">
                    <InputGroup label="Início"><input type="time" className="bg-black/20 border border-white/10 rounded-xl px-4 py-3 outline-none" value={newHorario.horario_inicio} onChange={e=>setNewHorario({...newHorario, horario_inicio: e.target.value})} /></InputGroup>
                    <InputGroup label="Fim"><input type="time" className="bg-black/20 border border-white/10 rounded-xl px-4 py-3 outline-none" value={newHorario.horario_fim} onChange={e=>setNewHorario({...newHorario, horario_fim: e.target.value})} /></InputGroup>
                  </div>
                  <button className="bg-[#4B39EF] px-8 py-3 rounded-xl font-bold h-[50px] hover:bg-[#5E47FF] transition-all">SALVAR NA GRADE</button>
               </form>
            </div>
          </div>
        )}

        {activeTab === 'professores' && (
          <div className="space-y-8">
            <h2 className="text-3xl font-bold text-white tracking-tight">Corpo Docente</h2>
            <div className="bg-[#1A1C1E] rounded-3xl border border-white/5 overflow-hidden shadow-2xl">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-white/5 text-gray-500 uppercase text-[10px] tracking-[0.2em]">
                    <th className="px-10 py-6">Nome Completo</th>
                    <th className="px-10 py-6">Departamento</th>
                    <th className="px-10 py-6">E-mail Corporativo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {professores.map(p => (
                    <tr key={p.professor_id} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-10 py-8">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center font-bold text-[#4B39EF]">{p.nome.charAt(0)}</div>
                          <span className="font-bold text-white">{p.nome}</span>
                        </div>
                      </td>
                      <td className="px-10 py-8 text-gray-400">{p.departamento}</td>
                      <td className="px-10 py-8 text-[#4B39EF]/80 font-medium group-hover:text-[#4B39EF] transition-all">{p.email}</td>
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
    <button onClick={onClick} className={`w-full flex items-center gap-3 px-4 py-4 rounded-2xl transition-all ${active ? 'bg-[#4B39EF] text-white shadow-xl shadow-[#4B39EF]/20' : 'text-gray-500 hover:bg-white/5 hover:text-white'}`}>
      {icon} <span className="font-bold text-sm">{label}</span>
    </button>
  );
}

function InputGroup({ label, children }) {
  return (
    <div className="space-y-2">
      <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-1">{label}</label>
      {children}
    </div>
  );
}
