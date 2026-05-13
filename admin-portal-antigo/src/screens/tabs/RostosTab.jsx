import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, Trash2, ScanFace, Database, ImageOff, ChevronLeft, ChevronRight, ChevronDown, ChevronRight as ChevronRightIcon } from 'lucide-react';
import { EmptyState } from '../../components/ui/EmptyState';
import { usePagination } from '../../hooks/usePagination';
import {
  listarRostosRekognition,
  listarRostosS3,
  excluirRostoRekognition,
  excluirRostosRekognitionBulk,
  excluirRostoS3,
} from '../../services/rostosService';
import { extractErrorMessage } from '../../services/apiClient';

const PAGE_SIZE = 10;

// Extrai external_id do S3 key: "alunos/{external_id}_{uuid32}.ext"
function extractExternalIdS3(key) {
  const filename = key.replace(/^alunos\//, '');
  const match = filename.match(/^(.+)_[0-9a-f]{32}\.(jpg|png)$/i);
  return match ? match[1] : filename;
}

function formatarTamanho(bytes) {
  if (bytes === 0 || bytes == null) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatarData(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
  } catch { return '—'; }
}

function truncarFaceId(id) {
  if (!id) return '—';
  return `${id.substring(0, 8)}...`;
}

function nomeArquivoS3(key) {
  if (!key) return '';
  return key.replace(/^alunos\//, '');
}

function Paginacao({ page, totalPages, setPage }) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-center gap-2 py-3 border-t border-white/5 flex-shrink-0">
      <button
        onClick={() => setPage((p) => Math.max(1, p - 1))}
        disabled={page === 1}
        className="w-8 h-8 rounded-xl bg-white/5 border border-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronLeft size={15} />
      </button>
      <span className="text-xs font-black text-gray-400 uppercase tracking-widest px-2">
        {page} / {totalPages}
      </span>
      <button
        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
        disabled={page === totalPages}
        className="w-8 h-8 rounded-xl bg-white/5 border border-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronRight size={15} />
      </button>
    </div>
  );
}

export function RostosTab({ showToast, showConfirm }) {
  const [rostos, setRostos] = useState([]);
  const [arquivos, setArquivos] = useState([]);
  const [loadingRostos, setLoadingRostos] = useState(false);
  const [loadingS3, setLoadingS3] = useState(false);
  const [selectedRostos, setSelectedRostos] = useState(new Set());
  const [selectedArquivos, setSelectedArquivos] = useState(new Set());
  const [expandedRekognition, setExpandedRekognition] = useState(new Set());
  const [expandedS3, setExpandedS3] = useState(new Set());

  const fetchRostos = useCallback(async () => {
    setLoadingRostos(true);
    setSelectedRostos(new Set());
    try {
      const data = await listarRostosRekognition();
      setRostos(Array.isArray(data) ? data : []);
    } catch (err) {
      showToast(`Erro ao carregar Rekognition: ${extractErrorMessage(err)}`, 'error');
    } finally {
      setLoadingRostos(false);
    }
  }, [showToast]);

  const fetchS3 = useCallback(async () => {
    setLoadingS3(true);
    setSelectedArquivos(new Set());
    try {
      const data = await listarRostosS3();
      setArquivos(Array.isArray(data) ? data : []);
    } catch (err) {
      showToast(`Erro ao carregar S3: ${extractErrorMessage(err)}`, 'error');
    } finally {
      setLoadingS3(false);
    }
  }, [showToast]);

  useEffect(() => { fetchRostos(); fetchS3(); }, [fetchRostos, fetchS3]);

  // Agrupar Rekognition por external_image_id
  const gruposRekognition = useMemo(() => {
    const map = new Map();
    for (const r of rostos) {
      const key = r.external_image_id || '—';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(r);
    }
    return Array.from(map.entries())
      .map(([nome, faces]) => ({ nome, faces }))
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR', { sensitivity: 'base' }));
  }, [rostos]);

  // Agrupar S3 por external_id extraído do key
  const gruposS3 = useMemo(() => {
    const map = new Map();
    for (const a of arquivos) {
      const key = extractExternalIdS3(a.key);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(a);
    }
    return Array.from(map.entries())
      .map(([nome, files]) => ({
        nome,
        files,
        totalSize: files.reduce((s, f) => s + (f.size || 0), 0),
        ultimaData: files.map((f) => f.last_modified).filter(Boolean).sort().pop() || null,
      }))
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR', { sensitivity: 'base' }));
  }, [arquivos]);

  const { page: pageRek, setPage: setPageRek, totalPages: totalPagesRek, paged: gruposRekPaged } =
    usePagination(gruposRekognition, PAGE_SIZE);
  const { page: pageS3, setPage: setPageS3, totalPages: totalPagesS3, paged: gruposS3Paged } =
    usePagination(gruposS3, PAGE_SIZE);

  // Toggle expansão de grupo
  const toggleExpandRek = (nome) =>
    setExpandedRekognition((prev) => { const n = new Set(prev); n.has(nome) ? n.delete(nome) : n.add(nome); return n; });
  const toggleExpandS3 = (nome) =>
    setExpandedS3((prev) => { const n = new Set(prev); n.has(nome) ? n.delete(nome) : n.add(nome); return n; });

  // Select individual
  const toggleRosto = (face_id) =>
    setSelectedRostos((prev) => { const n = new Set(prev); n.has(face_id) ? n.delete(face_id) : n.add(face_id); return n; });
  const toggleArquivo = (key) =>
    setSelectedArquivos((prev) => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; });

  // Select grupo inteiro
  const toggleGrupoRek = (grupo) =>
    setSelectedRostos((prev) => {
      const n = new Set(prev);
      const allSelected = grupo.faces.every((f) => n.has(f.face_id));
      grupo.faces.forEach((f) => allSelected ? n.delete(f.face_id) : n.add(f.face_id));
      return n;
    });
  const toggleGrupoS3 = (grupo) =>
    setSelectedArquivos((prev) => {
      const n = new Set(prev);
      const allSelected = grupo.files.every((f) => n.has(f.key));
      grupo.files.forEach((f) => allSelected ? n.delete(f.key) : n.add(f.key));
      return n;
    });

  // Select all visible (grupos da página atual)
  const allFacesPaged = gruposRekPaged.flatMap((g) => g.faces);
  const todosRekChecked = allFacesPaged.length > 0 && allFacesPaged.every((f) => selectedRostos.has(f.face_id));
  const algunsRekChecked = allFacesPaged.some((f) => selectedRostos.has(f.face_id));
  const toggleAllRek = () =>
    setSelectedRostos((prev) => {
      const n = new Set(prev);
      todosRekChecked
        ? allFacesPaged.forEach((f) => n.delete(f.face_id))
        : allFacesPaged.forEach((f) => n.add(f.face_id));
      return n;
    });

  const allArquivosPaged = gruposS3Paged.flatMap((g) => g.files);
  const todosS3Checked = allArquivosPaged.length > 0 && allArquivosPaged.every((f) => selectedArquivos.has(f.key));
  const algunsS3Checked = allArquivosPaged.some((f) => selectedArquivos.has(f.key));
  const toggleAllS3 = () =>
    setSelectedArquivos((prev) => {
      const n = new Set(prev);
      todosS3Checked
        ? allArquivosPaged.forEach((f) => n.delete(f.key))
        : allArquivosPaged.forEach((f) => n.add(f.key));
      return n;
    });

  // Handlers de exclusão
  const handleExcluirRosto = (face_id, nome) =>
    showConfirm('Excluir Rosto', `Excluir o rosto "${nome || truncarFaceId(face_id)}" da coleção Rekognition?`, async () => {
      try { await excluirRostoRekognition(face_id); showToast('Rosto removido.', 'success'); fetchRostos(); }
      catch (err) { showToast(`Erro ao excluir rosto: ${extractErrorMessage(err)}`, 'error'); }
    });

  const handleExcluirGrupoRek = (grupo) =>
    showConfirm('Excluir Aluno da Coleção', `Excluir todos os ${grupo.faces.length} rosto(s) de "${grupo.nome}" da coleção Rekognition?\n\nEsta ação é irreversível.`, async () => {
      try {
        const ids = grupo.faces.map((f) => f.face_id).filter(Boolean);
        await excluirRostosRekognitionBulk(ids);
        showToast(`${ids.length} rosto(s) de "${grupo.nome}" removido(s).`, 'success');
        fetchRostos();
      } catch (err) { showToast(`Erro ao excluir: ${extractErrorMessage(err)}`, 'error'); }
    });

  const handleExcluirTodosRostos = () => {
    if (rostos.length === 0) return;
    showConfirm('Excluir Todos os Rostos', `Excluir TODOS os ${rostos.length} rosto(s) da coleção Rekognition?\n\nEsta ação é irreversível.`, async () => {
      try {
        const ids = rostos.map((r) => r.face_id).filter(Boolean);
        await excluirRostosRekognitionBulk(ids);
        showToast(`${ids.length} rosto(s) removido(s).`, 'success');
        fetchRostos();
      } catch (err) { showToast(`Erro ao excluir rostos: ${extractErrorMessage(err)}`, 'error'); }
    });
  };

  const handleExcluirSelecionadosRostos = () => {
    if (selectedRostos.size === 0) return;
    showConfirm('Excluir Selecionados', `Excluir ${selectedRostos.size} rosto(s) selecionado(s)?`, async () => {
      try {
        await excluirRostosRekognitionBulk([...selectedRostos]);
        showToast(`${selectedRostos.size} rosto(s) removido(s).`, 'success');
        fetchRostos();
      } catch (err) { showToast(`Erro: ${extractErrorMessage(err)}`, 'error'); }
    });
  };

  const handleExcluirArquivo = (key) =>
    showConfirm('Excluir Arquivo S3', `Excluir "${nomeArquivoS3(key)}" do bucket?\n\nEsta ação é irreversível.`, async () => {
      try { await excluirRostoS3(key); showToast('Arquivo removido.', 'success'); fetchS3(); }
      catch (err) { showToast(`Erro ao excluir: ${extractErrorMessage(err)}`, 'error'); }
    });

  const handleExcluirGrupoS3 = (grupo) =>
    showConfirm('Excluir Aluno do S3', `Excluir todos os ${grupo.files.length} arquivo(s) de "${grupo.nome}" do bucket?\n\nEsta ação é irreversível.`, async () => {
      try {
        await Promise.all(grupo.files.map((f) => excluirRostoS3(f.key)));
        showToast(`${grupo.files.length} arquivo(s) de "${grupo.nome}" removido(s).`, 'success');
        fetchS3();
      } catch (err) { showToast(`Erro: ${extractErrorMessage(err)}`, 'error'); }
    });

  const handleExcluirSelecionadosS3 = () => {
    if (selectedArquivos.size === 0) return;
    showConfirm('Excluir Selecionados', `Excluir ${selectedArquivos.size} arquivo(s) selecionado(s)?`, async () => {
      try {
        await Promise.all([...selectedArquivos].map((key) => excluirRostoS3(key)));
        showToast(`${selectedArquivos.size} arquivo(s) removido(s).`, 'success');
        fetchS3();
      } catch (err) { showToast(`Erro: ${extractErrorMessage(err)}`, 'error'); }
    });
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col min-h-0">
      <h2 className="text-2xl font-black text-white tracking-tight mb-4 flex-shrink-0">Rostos AWS</h2>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 flex-1 overflow-hidden min-h-0">

        {/* REKOGNITION */}
        <div className="bg-[#151718] rounded-[32px] border border-white/5 shadow-2xl flex flex-col overflow-hidden min-h-0">
          <div className="flex items-center justify-between px-4 py-4 border-b border-white/5 flex-shrink-0 gap-2">
            <div className="flex items-center gap-2 min-w-0 overflow-hidden">
              <div className="w-9 h-9 shrink-0 bg-[#4B39EF]/10 rounded-xl flex items-center justify-center text-[#4B39EF]">
                <ScanFace size={18} />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-black text-white tracking-tight truncate">Rekognition Collection</h3>
                <p className="text-xs text-gray-500 font-bold uppercase tracking-widest hidden 2xl:block">Coleção de rostos indexados</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="bg-white/5 px-2.5 py-1.5 rounded-lg text-xs font-black text-gray-300 border border-white/5 uppercase tracking-widest whitespace-nowrap">
                {gruposRekognition.length} aluno{gruposRekognition.length !== 1 ? 's' : ''} • {rostos.length} foto{rostos.length !== 1 ? 's' : ''}
              </span>
              <button onClick={fetchRostos} disabled={loadingRostos} title="Atualizar"
                className="w-8 h-8 bg-white/5 rounded-xl flex items-center justify-center text-gray-400 hover:text-[#4B39EF] transition-all border border-white/5 hover:border-[#4B39EF]/30 disabled:opacity-50">
                <RefreshCw size={15} className={loadingRostos ? 'animate-spin' : ''} />
              </button>
              {selectedRostos.size > 0 && (
                <button onClick={handleExcluirSelecionadosRostos}
                  className="px-2.5 h-8 bg-red-500/20 rounded-xl flex items-center gap-1.5 text-xs font-black text-red-400 hover:bg-red-500/30 transition-all border border-red-500/30 uppercase tracking-widest whitespace-nowrap">
                  <Trash2 size={13} /> Excluir {selectedRostos.size}
                </button>
              )}
              {rostos.length > 0 && selectedRostos.size === 0 && (
                <button onClick={handleExcluirTodosRostos}
                  className="px-2.5 h-8 bg-red-500/10 rounded-xl flex items-center gap-1.5 text-xs font-black text-red-400 hover:bg-red-500/20 transition-all border border-red-500/20 uppercase tracking-widest whitespace-nowrap">
                  <Trash2 size={13} /> Excluir Todos
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {loadingRostos ? (
              <div className="py-12 text-center text-gray-500 font-black">Carregando rostos...</div>
            ) : gruposRekognition.length === 0 ? (
              <EmptyState icon={ScanFace} message="Nenhum rosto indexado" />
            ) : (
              <table className="w-full text-left table-fixed">
                <thead>
                  <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                    <th className="px-4 py-3 rounded-l-xl w-10">
                      <input type="checkbox" checked={todosRekChecked}
                        ref={(el) => { if (el) el.indeterminate = algunsRekChecked && !todosRekChecked; }}
                        onChange={toggleAllRek}
                        className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer" />
                    </th>
                    <th className="px-4 py-3">Aluno</th>
                    <th className="px-4 py-3 w-20 rounded-r-xl text-right">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {gruposRekPaged.map((grupo) => {
                    const expanded = expandedRekognition.has(grupo.nome);
                    const allChecked = grupo.faces.every((f) => selectedRostos.has(f.face_id));
                    const someChecked = grupo.faces.some((f) => selectedRostos.has(f.face_id));
                    return (
                      <React.Fragment key={grupo.nome}>
                        {/* Linha do grupo */}
                        <tr className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                          <td className="px-4 py-3">
                            <input type="checkbox" checked={allChecked}
                              ref={(el) => { if (el) el.indeterminate = someChecked && !allChecked; }}
                              onChange={() => toggleGrupoRek(grupo)}
                              className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer" />
                          </td>
                          <td className="px-4 py-3">
                            <button className="flex items-center gap-3 w-full text-left" onClick={() => toggleExpandRek(grupo.nome)}>
                              <div className="w-9 h-9 bg-gradient-to-br from-[#4B39EF] to-[#5E47FF] rounded-xl flex items-center justify-center font-black text-white text-sm shadow-lg shrink-0">
                                {grupo.nome.charAt(0).toUpperCase()}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-black text-white text-sm truncate" title={grupo.nome}>{grupo.nome}</p>
                                <p className="text-xs text-gray-500 font-bold mt-0.5">{grupo.faces.length} foto{grupo.faces.length !== 1 ? 's' : ''}</p>
                              </div>
                              {expanded
                                ? <ChevronDown size={15} className="text-gray-500 shrink-0" />
                                : <ChevronRightIcon size={15} className="text-gray-500 shrink-0" />}
                            </button>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button onClick={() => handleExcluirGrupoRek(grupo)} title="Excluir aluno"
                              className="w-9 h-9 bg-white/5 rounded-xl inline-flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30">
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                        {/* Sub-linhas expandidas */}
                        {expanded && grupo.faces.map((f) => (
                          <tr key={f.face_id} onClick={() => toggleRosto(f.face_id)}
                            className={`border-t border-white/[0.03] cursor-pointer transition-colors ${selectedRostos.has(f.face_id) ? 'bg-[#4B39EF]/10' : 'hover:bg-white/[0.01]'}`}>
                            <td className="pl-9 pr-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                              <input type="checkbox" checked={selectedRostos.has(f.face_id)}
                                onChange={() => toggleRosto(f.face_id)}
                                className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer" />
                            </td>
                            <td className="px-4 py-2.5">
                              <div className="flex items-center gap-3 pl-4 border-l-2 border-white/10">
                                <span className="bg-white/5 px-3 py-1 rounded-lg text-xs font-black text-gray-400 border border-white/5 font-mono">
                                  {f.face_id}
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-2.5 text-right" onClick={(e) => e.stopPropagation()}>
                              <button onClick={() => handleExcluirRosto(f.face_id, grupo.nome)} title="Excluir face"
                                className="w-8 h-8 bg-white/5 rounded-xl inline-flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30">
                                <Trash2 size={13} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          <Paginacao page={pageRek} totalPages={totalPagesRek} setPage={setPageRek} />
        </div>

        {/* S3 SECTION */}
        <div className="bg-[#151718] rounded-[32px] border border-white/5 shadow-2xl flex flex-col overflow-hidden min-h-0">
          <div className="flex items-center justify-between px-4 py-4 border-b border-white/5 flex-shrink-0 gap-2">
            <div className="flex items-center gap-2 min-w-0 overflow-hidden">
              <div className="w-9 h-9 shrink-0 bg-amber-500/10 rounded-xl flex items-center justify-center text-amber-500">
                <Database size={18} />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-black text-white tracking-tight truncate">S3 Bucket (alunos/)</h3>
                <p className="text-xs text-gray-500 font-bold uppercase tracking-widest hidden 2xl:block">Imagens armazenadas</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="bg-white/5 px-2.5 py-1.5 rounded-lg text-xs font-black text-gray-300 border border-white/5 uppercase tracking-widest whitespace-nowrap">
                {gruposS3.length} aluno{gruposS3.length !== 1 ? 's' : ''} • {arquivos.length} arquivo{arquivos.length !== 1 ? 's' : ''}
              </span>
              <button onClick={fetchS3} disabled={loadingS3} title="Atualizar"
                className="w-8 h-8 bg-white/5 rounded-xl flex items-center justify-center text-gray-400 hover:text-[#4B39EF] transition-all border border-white/5 hover:border-[#4B39EF]/30 disabled:opacity-50">
                <RefreshCw size={15} className={loadingS3 ? 'animate-spin' : ''} />
              </button>
              {selectedArquivos.size > 0 && (
                <button onClick={handleExcluirSelecionadosS3}
                  className="px-2.5 h-8 bg-red-500/20 rounded-xl flex items-center gap-1.5 text-xs font-black text-red-400 hover:bg-red-500/30 transition-all border border-red-500/30 uppercase tracking-widest whitespace-nowrap">
                  <Trash2 size={13} /> Excluir {selectedArquivos.size}
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 [scrollbar-gutter:stable]">
            {loadingS3 ? (
              <div className="py-12 text-center text-gray-500 font-black">Carregando arquivos...</div>
            ) : gruposS3.length === 0 ? (
              <EmptyState icon={ImageOff} message="Nenhum arquivo encontrado" />
            ) : (
              <table className="w-full text-left table-fixed">
                <thead>
                  <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                    <th className="px-4 py-3 rounded-l-xl w-10">
                      <input type="checkbox" checked={todosS3Checked}
                        ref={(el) => { if (el) el.indeterminate = algunsS3Checked && !todosS3Checked; }}
                        onChange={toggleAllS3}
                        className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer" />
                    </th>
                    <th className="px-4 py-3">Aluno</th>
                    <th className="px-4 py-3 w-24">Tamanho</th>
                    <th className="px-4 py-3 w-20 rounded-r-xl text-right">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {gruposS3Paged.map((grupo) => {
                    const expanded = expandedS3.has(grupo.nome);
                    const allChecked = grupo.files.every((f) => selectedArquivos.has(f.key));
                    const someChecked = grupo.files.some((f) => selectedArquivos.has(f.key));
                    return (
                      <React.Fragment key={grupo.nome}>
                        {/* Linha do grupo */}
                        <tr className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                          <td className="px-4 py-3">
                            <input type="checkbox" checked={allChecked}
                              ref={(el) => { if (el) el.indeterminate = someChecked && !allChecked; }}
                              onChange={() => toggleGrupoS3(grupo)}
                              className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer" />
                          </td>
                          <td className="px-4 py-3">
                            <button className="flex items-center gap-3 w-full text-left" onClick={() => toggleExpandS3(grupo.nome)}>
                              <div className="w-9 h-9 bg-gradient-to-br from-amber-500 to-[#4B39EF] rounded-xl flex items-center justify-center font-black text-white text-sm shadow-lg shrink-0">
                                {grupo.nome.charAt(0).toUpperCase()}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-black text-white text-sm truncate" title={grupo.nome}>{grupo.nome}</p>
                                <p className="text-xs text-gray-500 font-bold mt-0.5">
                                  {grupo.files.length} arquivo{grupo.files.length !== 1 ? 's' : ''}
                                  {grupo.ultimaData && <span className="ml-2">• {formatarData(grupo.ultimaData)}</span>}
                                </p>
                              </div>
                              {expanded
                                ? <ChevronDown size={15} className="text-gray-500 shrink-0" />
                                : <ChevronRightIcon size={15} className="text-gray-500 shrink-0" />}
                            </button>
                          </td>
                          <td className="px-4 py-3">
                            <span className="bg-white/5 px-2.5 py-1 rounded-lg text-xs font-black text-gray-400 border border-white/5 whitespace-nowrap">
                              {formatarTamanho(grupo.totalSize)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button onClick={() => handleExcluirGrupoS3(grupo)} title="Excluir aluno"
                              className="w-9 h-9 bg-white/5 rounded-xl inline-flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30">
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                        {/* Sub-linhas expandidas */}
                        {expanded && grupo.files.map((a) => (
                          <tr key={a.key} onClick={() => toggleArquivo(a.key)}
                            className={`border-t border-white/[0.03] cursor-pointer transition-colors ${selectedArquivos.has(a.key) ? 'bg-[#4B39EF]/10' : 'hover:bg-white/[0.01]'}`}>
                            <td className="pl-9 pr-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                              <input type="checkbox" checked={selectedArquivos.has(a.key)}
                                onChange={() => toggleArquivo(a.key)}
                                className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer" />
                            </td>
                            <td className="px-4 py-2.5">
                              <div className="flex items-center gap-2 pl-4 border-l-2 border-white/10">
                                <p className="text-xs font-bold text-gray-400 truncate font-mono" title={a.key}>
                                  {nomeArquivoS3(a.key)}
                                </p>
                              </div>
                            </td>
                            <td className="px-4 py-2.5">
                              <span className="text-xs font-bold text-gray-500">{formatarTamanho(a.size)}</span>
                            </td>
                            <td className="px-4 py-2.5 text-right" onClick={(e) => e.stopPropagation()}>
                              <button onClick={() => handleExcluirArquivo(a.key)} title="Excluir arquivo"
                                className="w-8 h-8 bg-white/5 rounded-xl inline-flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30">
                                <Trash2 size={13} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          <Paginacao page={pageS3} totalPages={totalPagesS3} setPage={setPageS3} />
        </div>

      </div>
    </div>
  );
}
