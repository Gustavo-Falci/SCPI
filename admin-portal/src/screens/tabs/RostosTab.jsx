import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Trash2, ScanFace, Database, ImageOff } from 'lucide-react';
import { EmptyState } from '../../components/ui/EmptyState';
import {
  listarRostosRekognition,
  listarRostosS3,
  excluirRostoRekognition,
  excluirRostosRekognitionBulk,
  excluirRostoS3,
} from '../../services/rostosService';
import { extractErrorMessage } from '../../services/apiClient';

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
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
  } catch {
    return '—';
  }
}

function truncarFaceId(id) {
  if (!id) return '—';
  return `${id.substring(0, 8)}...`;
}

function nomeArquivoS3(key) {
  if (!key) return '';
  return key.replace(/^alunos\//, '');
}

export function RostosTab({ showToast, showConfirm }) {
  const [rostos, setRostos] = useState([]);
  const [arquivos, setArquivos] = useState([]);
  const [loadingRostos, setLoadingRostos] = useState(false);
  const [loadingS3, setLoadingS3] = useState(false);
  const [selectedRostos, setSelectedRostos] = useState(new Set());
  const [selectedArquivos, setSelectedArquivos] = useState(new Set());

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

  const toggleRosto = (face_id) =>
    setSelectedRostos((prev) => {
      const next = new Set(prev);
      next.has(face_id) ? next.delete(face_id) : next.add(face_id);
      return next;
    });

  const toggleAllRostos = () =>
    setSelectedRostos((prev) =>
      prev.size === rostos.length ? new Set() : new Set(rostos.map((r) => r.face_id))
    );

  const toggleArquivo = (key) =>
    setSelectedArquivos((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  const toggleAllArquivos = () =>
    setSelectedArquivos((prev) =>
      prev.size === arquivos.length ? new Set() : new Set(arquivos.map((a) => a.key))
    );

  useEffect(() => {
    fetchRostos();
    fetchS3();
  }, [fetchRostos, fetchS3]);

  const handleExcluirRosto = (face_id, nome) => {
    showConfirm(
      'Excluir Rosto',
      `Deseja realmente excluir o rosto "${nome || truncarFaceId(face_id)}" da coleção Rekognition?`,
      async () => {
        try {
          await excluirRostoRekognition(face_id);
          showToast('Rosto removido com sucesso.', 'success');
          fetchRostos();
        } catch (err) {
          showToast(`Erro ao excluir rosto: ${extractErrorMessage(err)}`, 'error');
        }
      }
    );
  };

  const handleExcluirTodosRostos = () => {
    if (rostos.length === 0) return;
    showConfirm(
      'Excluir Todos os Rostos',
      `Deseja realmente excluir TODOS os ${rostos.length} rosto(s) da coleção Rekognition?\n\nEsta ação é irreversível.`,
      async () => {
        try {
          const face_ids = rostos.map((r) => r.face_id).filter(Boolean);
          await excluirRostosRekognitionBulk(face_ids);
          showToast(`${face_ids.length} rosto(s) removido(s) com sucesso.`, 'success');
          fetchRostos();
        } catch (err) {
          showToast(`Erro ao excluir rostos: ${extractErrorMessage(err)}`, 'error');
        }
      }
    );
  };

  const handleExcluirSelecionadosRostos = () => {
    if (selectedRostos.size === 0) return;
    showConfirm(
      'Excluir Rostos Selecionados',
      `Deseja realmente excluir ${selectedRostos.size} rosto(s) selecionado(s) da coleção Rekognition?`,
      async () => {
        try {
          await excluirRostosRekognitionBulk([...selectedRostos]);
          showToast(`${selectedRostos.size} rosto(s) removido(s) com sucesso.`, 'success');
          fetchRostos();
        } catch (err) {
          showToast(`Erro ao excluir rostos: ${extractErrorMessage(err)}`, 'error');
        }
      }
    );
  };

  const handleExcluirSelecionadosS3 = () => {
    if (selectedArquivos.size === 0) return;
    showConfirm(
      'Excluir Arquivos Selecionados',
      `Deseja realmente excluir ${selectedArquivos.size} arquivo(s) selecionado(s) do bucket S3?`,
      async () => {
        try {
          await Promise.all([...selectedArquivos].map((key) => excluirRostoS3(key)));
          showToast(`${selectedArquivos.size} arquivo(s) removido(s) com sucesso.`, 'success');
          fetchS3();
        } catch (err) {
          showToast(`Erro ao excluir arquivos: ${extractErrorMessage(err)}`, 'error');
        }
      }
    );
  };

  const handleExcluirArquivo = (key) => {
    const nome = nomeArquivoS3(key);
    showConfirm(
      'Excluir Arquivo S3',
      `Deseja realmente excluir o arquivo "${nome}" do bucket?\n\nEsta ação é irreversível.`,
      async () => {
        try {
          await excluirRostoS3(key);
          showToast('Arquivo removido com sucesso.', 'success');
          fetchS3();
        } catch (err) {
          showToast(`Erro ao excluir arquivo: ${extractErrorMessage(err)}`, 'error');
        }
      }
    );
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col min-h-0">
      <h2 className="text-2xl font-black text-white tracking-tight mb-4 flex-shrink-0">Rostos AWS</h2>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 flex-1 overflow-hidden min-h-0">

        {/* REKOGNITION SECTION */}
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
                {rostos.length} rosto{rostos.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={fetchRostos}
                disabled={loadingRostos}
                title="Atualizar"
                className="w-8 h-8 bg-white/5 rounded-xl flex items-center justify-center text-gray-400 hover:text-[#4B39EF] transition-all border border-white/5 hover:border-[#4B39EF]/30 disabled:opacity-50"
              >
                <RefreshCw size={15} className={loadingRostos ? 'animate-spin' : ''} />
              </button>
              {selectedRostos.size > 0 && (
                <button
                  onClick={handleExcluirSelecionadosRostos}
                  className="px-2.5 h-8 bg-red-500/20 rounded-xl flex items-center gap-1.5 text-xs font-black text-red-400 hover:bg-red-500/30 transition-all border border-red-500/30 uppercase tracking-widest whitespace-nowrap"
                >
                  <Trash2 size={13} /> Excluir {selectedRostos.size}
                </button>
              )}
              {rostos.length > 0 && selectedRostos.size === 0 && (
                <button
                  onClick={handleExcluirTodosRostos}
                  className="px-2.5 h-8 bg-red-500/10 rounded-xl flex items-center gap-1.5 text-xs font-black text-red-400 hover:bg-red-500/20 transition-all border border-red-500/20 uppercase tracking-widest whitespace-nowrap"
                >
                  <Trash2 size={13} /> Excluir Todos
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {loadingRostos ? (
              <div className="flex-1 flex items-center justify-center py-12">
                <p className="text-gray-500 font-black text-base">Carregando rostos...</p>
              </div>
            ) : rostos.length === 0 ? (
              <EmptyState icon={ScanFace} message="Nenhum rosto indexado" />
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                    <th className="px-4 py-3 rounded-l-xl w-10">
                      <input
                        type="checkbox"
                        checked={rostos.length > 0 && selectedRostos.size === rostos.length}
                        onChange={toggleAllRostos}
                        className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer"
                      />
                    </th>
                    <th className="px-4 py-3">External Image Id</th>
                    <th className="px-4 py-3">Face Id</th>
                    <th className="px-4 py-3 rounded-r-xl text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {rostos.map((r) => (
                    <tr
                      key={r.face_id}
                      onClick={() => toggleRosto(r.face_id)}
                      className={`transition-colors cursor-pointer ${selectedRostos.has(r.face_id) ? 'bg-[#4B39EF]/10' : 'hover:bg-white/[0.01]'}`}
                    >
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedRostos.has(r.face_id)}
                          onChange={() => toggleRosto(r.face_id)}
                          className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 bg-gradient-to-br from-[#4B39EF] to-[#5E47FF] rounded-xl flex items-center justify-center font-black text-white text-sm shadow-lg shrink-0">
                            {(r.external_image_id || '?').charAt(0).toUpperCase()}
                          </div>
                          <p className="font-black text-white text-sm truncate max-w-[180px]" title={r.external_image_id || '—'}>
                            {r.external_image_id || '—'}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className="bg-white/5 px-3 py-1 rounded-lg text-xs font-black text-gray-400 border border-white/5 uppercase tracking-widest font-mono"
                          title={r.face_id}
                        >
                          {truncarFaceId(r.face_id)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleExcluirRosto(r.face_id, r.external_image_id)}
                          title="Excluir rosto"
                          className="w-9 h-9 bg-white/5 rounded-xl inline-flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* S3 SECTION */}
        <div className="bg-[#151718] rounded-[32px] border border-white/5 shadow-2xl flex flex-col overflow-hidden min-h-0">
          <div className="flex items-center justify-between px-6 py-5 border-b border-white/5 flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center text-amber-500">
                <Database size={20} />
              </div>
              <div>
                <h3 className="text-base font-black text-white tracking-tight">S3 Bucket (alunos/)</h3>
                <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">Imagens armazenadas</p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap justify-end">
              <span className="bg-white/5 px-3 py-1.5 rounded-lg text-xs font-black text-gray-300 border border-white/5 uppercase tracking-widest">
                {arquivos.length} arquivo{arquivos.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={fetchS3}
                disabled={loadingS3}
                title="Atualizar"
                className="w-9 h-9 bg-white/5 rounded-xl flex items-center justify-center text-gray-400 hover:text-[#4B39EF] transition-all border border-white/5 hover:border-[#4B39EF]/30 disabled:opacity-50"
              >
                <RefreshCw size={16} className={loadingS3 ? 'animate-spin' : ''} />
              </button>
              {selectedArquivos.size > 0 && (
                <button
                  onClick={handleExcluirSelecionadosS3}
                  className="px-3 h-9 bg-red-500/20 rounded-xl flex items-center gap-2 text-xs font-black text-red-400 hover:bg-red-500/30 transition-all border border-red-500/30 uppercase tracking-widest"
                >
                  <Trash2 size={14} /> Excluir {selectedArquivos.size}
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 [scrollbar-gutter:stable]">
            {loadingS3 ? (
              <div className="flex-1 flex items-center justify-center py-12">
                <p className="text-gray-500 font-black text-base">Carregando arquivos...</p>
              </div>
            ) : arquivos.length === 0 ? (
              <EmptyState icon={ImageOff} message="Nenhum arquivo encontrado" />
            ) : (
              <table className="w-full text-left table-fixed">
                <thead>
                  <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                    <th className="px-4 py-3 rounded-l-xl w-10">
                      <input
                        type="checkbox"
                        checked={arquivos.length > 0 && selectedArquivos.size === arquivos.length}
                        onChange={toggleAllArquivos}
                        className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer"
                      />
                    </th>
                    <th className="px-4 py-3">Arquivo</th>
                    <th className="px-4 py-3 w-[18%]">Tamanho</th>
                    <th className="px-4 py-3 w-[18%]">Data</th>
                    <th className="px-4 py-3 w-[10%] rounded-r-xl text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {arquivos.map((a) => (
                    <tr
                      key={a.key}
                      onClick={() => toggleArquivo(a.key)}
                      className={`transition-colors cursor-pointer ${selectedArquivos.has(a.key) ? 'bg-[#4B39EF]/10' : 'hover:bg-white/[0.01]'}`}
                    >
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedArquivos.has(a.key)}
                          onChange={() => toggleArquivo(a.key)}
                          className="w-4 h-4 rounded accent-[#4B39EF] cursor-pointer"
                        />
                      </td>
                      <td className="px-4 py-3 overflow-hidden">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-9 h-9 bg-gradient-to-br from-amber-500 to-[#4B39EF] rounded-xl flex items-center justify-center font-black text-white text-xs shadow-lg shrink-0">
                            IMG
                          </div>
                          <p className="font-black text-white text-sm truncate" title={a.key}>
                            {nomeArquivoS3(a.key)}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="bg-white/5 px-3 py-1 rounded-lg text-xs font-black text-gray-400 border border-white/5 uppercase tracking-widest">
                          {formatarTamanho(a.size)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-300 font-bold text-sm whitespace-nowrap">
                        {formatarData(a.last_modified)}
                      </td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleExcluirArquivo(a.key)}
                          title="Excluir arquivo"
                          className="w-9 h-9 bg-white/5 rounded-xl inline-flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
