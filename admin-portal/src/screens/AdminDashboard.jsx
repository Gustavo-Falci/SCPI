import React, { useState } from 'react';
import { Sidebar } from '../components/layout/Sidebar';
import { DashboardHeader } from '../components/layout/DashboardHeader';
import { Toast } from '../components/ui/Toast';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { HorarioModal } from '../components/modals/HorarioModal';
import { ProfessorAssignModal } from '../components/modals/ProfessorAssignModal';
import { MatriculaModal } from '../components/modals/MatriculaModal';
import { SenhaTemporariaModal } from '../components/modals/SenhaTemporariaModal';
import { RelatorioDetalheModal } from '../components/modals/RelatorioDetalheModal';
import { TurmasTab } from './tabs/TurmasTab';
import { HorariosTab } from './tabs/HorariosTab';
import { ProfessoresTab } from './tabs/ProfessoresTab';
import { AlunosTab } from './tabs/AlunosTab';
import { RelatoriosTab } from './tabs/RelatoriosTab';
import { RostosTab } from './tabs/RostosTab';
import { useToast } from '../hooks/useToast';
import { useConfirm } from '../hooks/useConfirm';
import { DashboardDataProvider, useDashboardData } from '../contexts/DashboardDataContext';

function DashboardInner({ admin, onLogout }) {
  const [activeTab, setActiveTab] = useState('turmas');

  const { toast, showToast, dismissToast } = useToast();
  const { confirmDialog, showConfirm, dismissConfirm, handleConfirm } = useConfirm();

  const {
    turmas, professores, grade, refetchTurmasProfsGrade,
    filterTurno, setFilterTurno,
    filterSemestre, setFilterSemestre,
  } = useDashboardData();

  const [horarioModal, setHorarioModal] = useState(null);
  const [professorModal, setProfessorModal] = useState(null);
  const [matriculaModal, setMatriculaModal] = useState(null);
  const [senhaTemporariaModal, setSenhaTemporariaModal] = useState(null);
  const [relatorioExpandido, setRelatorioExpandido] = useState(null);

  return (
    <div className="flex h-screen bg-[#0C0C12] text-gray-200 font-sans">
      <Toast toast={toast} onDismiss={dismissToast} />
      <ConfirmDialog dialog={confirmDialog} onCancel={dismissConfirm} onConfirm={handleConfirm} />

      <Sidebar admin={admin} activeTab={activeTab} onChangeTab={setActiveTab} onLogout={onLogout} />

      <main className="flex-1 overflow-hidden bg-[#0C0C12] p-6 flex flex-col">
        <DashboardHeader
          activeTab={activeTab}
          filterTurno={filterTurno}
          onChangeTurno={setFilterTurno}
          filterSemestre={filterSemestre}
          onChangeSemestre={setFilterSemestre}
        />

        {activeTab === 'turmas' && (
          <TurmasTab
            showToast={showToast}
            showConfirm={showConfirm}
            onOpenProfessorModal={setProfessorModal}
            onOpenMatriculaModal={setMatriculaModal}
          />
        )}

        {activeTab === 'horarios' && (
          <HorariosTab
            showToast={showToast}
            showConfirm={showConfirm}
            onOpenHorarioModal={(dia_semana) => setHorarioModal({ dia_semana })}
          />
        )}

        {activeTab === 'professores' && (
          <ProfessoresTab
            showToast={showToast}
            showConfirm={showConfirm}
            onCreatedComSenha={setSenhaTemporariaModal}
          />
        )}

        {activeTab === 'alunos' && (
          <AlunosTab
            showToast={showToast}
            showConfirm={showConfirm}
            onCreatedComSenha={setSenhaTemporariaModal}
          />
        )}

        {activeTab === 'relatorios' && (
          <RelatoriosTab
            showToast={showToast}
            onOpenDetalhe={setRelatorioExpandido}
          />
        )}

        {activeTab === 'rostos' && (
          <RostosTab showToast={showToast} showConfirm={showConfirm} />
        )}

        <HorarioModal
          open={!!horarioModal}
          onClose={() => setHorarioModal(null)}
          dia_semana={horarioModal?.dia_semana}
          turno={filterTurno}
          turmas={turmas}
          grade={grade}
          showToast={showToast}
          onSuccess={() => { setHorarioModal(null); refetchTurmasProfsGrade(); }}
        />

        <ProfessorAssignModal
          turma={professorModal}
          professores={professores}
          onClose={() => setProfessorModal(null)}
          onSuccess={() => { setProfessorModal(null); refetchTurmasProfsGrade(); }}
          showToast={showToast}
        />

        <MatriculaModal
          turma={matriculaModal}
          onClose={() => setMatriculaModal(null)}
          onSuccess={() => { setMatriculaModal(null); refetchTurmasProfsGrade(); }}
          showToast={showToast}
        />

        <RelatorioDetalheModal
          data={relatorioExpandido}
          onClose={() => setRelatorioExpandido(null)}
        />

        <SenhaTemporariaModal
          data={senhaTemporariaModal}
          onClose={() => setSenhaTemporariaModal(null)}
          showToast={showToast}
        />
      </main>
    </div>
  );
}

export function AdminDashboard({ admin, onLogout }) {
  return (
    <DashboardDataProvider>
      <DashboardInner admin={admin} onLogout={onLogout} />
    </DashboardDataProvider>
  );
}
