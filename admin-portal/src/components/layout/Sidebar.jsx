import React from 'react';
import {
  LayoutDashboard, Calendar, Users, GraduationCap, FileText, LogOut,
} from 'lucide-react';

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

export function Sidebar({ admin, activeTab, onChangeTab, onLogout }) {
  return (
    <aside className="w-80 bg-[#151718] border-r border-white/5 flex flex-col shadow-2xl">
      <div className="p-12">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-[#4B39EF] rounded-2xl flex items-center justify-center font-black text-white text-2xl shadow-xl shadow-[#4B39EF]/30">S</div>
          <h1 className="text-2xl font-black text-white tracking-tighter">SCPI <span className="text-[#4B39EF]">CORE</span></h1>
        </div>
      </div>

      <nav className="flex-1 px-6 space-y-4">
        <SidebarItem icon={<LayoutDashboard size={24} />} label="Turmas & Matrículas" active={activeTab === 'turmas'} onClick={() => onChangeTab('turmas')} />
        <SidebarItem icon={<Calendar size={24} />} label="Grade Semanal" active={activeTab === 'horarios'} onClick={() => onChangeTab('horarios')} />
        <SidebarItem icon={<Users size={24} />} label="Professores" active={activeTab === 'professores'} onClick={() => onChangeTab('professores')} />
        <SidebarItem icon={<GraduationCap size={24} />} label="Alunos" active={activeTab === 'alunos'} onClick={() => onChangeTab('alunos')} />
        <SidebarItem icon={<FileText size={24} />} label="Relatórios" active={activeTab === 'relatorios'} onClick={() => onChangeTab('relatorios')} />
      </nav>

      <div className="p-8 border-t border-white/5">
        <div className="flex items-center gap-4 p-5 bg-white/[0.03] rounded-[24px] mb-8">
          <div className="w-12 h-12 bg-gradient-to-tr from-[#4B39EF] to-[#5E47FF] rounded-full flex items-center justify-center font-bold text-white text-lg uppercase">
            {admin?.user_name.charAt(0)}
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-sm font-black text-white truncate">{admin?.user_name}</p>
            <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">Administrador</p>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="flex items-center gap-4 text-gray-500 hover:text-red-400 transition-all w-full px-4 py-4 font-black text-xs uppercase tracking-widest"
        >
          <LogOut size={20} /> Sair do Sistema
        </button>
      </div>
    </aside>
  );
}
