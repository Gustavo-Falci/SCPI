import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StatusBar,
  Modal,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useFocusEffect } from "expo-router";
import DateTimePicker from "@react-native-community/datetimepicker";
import * as Sharing from "expo-sharing";
import * as Haptics from "expo-haptics";

import { apiGet, apiDownload } from "../../services/api";
import { useErrorToast } from "../../hooks/useErrorToast";
import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";

type Filtros = {
  dataInicio?: string; // YYYY-MM-DD
  dataFim?: string; // YYYY-MM-DD
  turmaId?: string;
  turno?: "Matutino" | "Noturno";
  semestre?: string;
};

type TurmaOpcao = { turma_id: string; nome_disciplina: string; codigo_turma: string };
type Opcoes = { turmas: TurmaOpcao[]; turnos: string[]; semestres: string[] };

function fmtISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fmtBR(iso?: string): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function buildQuery(f: Filtros): string {
  const p = new URLSearchParams();
  if (f.dataInicio) p.append("data_inicio", f.dataInicio);
  if (f.dataFim) p.append("data_fim", f.dataFim);
  if (f.turmaId) p.append("turma_id", f.turmaId);
  if (f.turno) p.append("turno", f.turno);
  if (f.semestre) p.append("semestre", f.semestre);
  const qs = p.toString();
  return qs ? `?${qs}` : "";
}

function contarAtivos(f: Filtros): number {
  let n = 0;
  if (f.dataInicio || f.dataFim) n++;
  if (f.turmaId) n++;
  if (f.turno) n++;
  if (f.semestre) n++;
  return n;
}

type Preset = "hoje" | "7dias" | "30dias" | "mes";

function calcPreset(p: Preset): { dataInicio: string; dataFim: string } {
  const hoje = new Date();
  const fim = fmtISO(hoje);
  if (p === "hoje") return { dataInicio: fim, dataFim: fim };
  if (p === "7dias") {
    const ini = new Date(hoje);
    ini.setDate(hoje.getDate() - 6);
    return { dataInicio: fmtISO(ini), dataFim: fim };
  }
  if (p === "30dias") {
    const ini = new Date(hoje);
    ini.setDate(hoje.getDate() - 29);
    return { dataInicio: fmtISO(ini), dataFim: fim };
  }
  // mes
  const ini = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
  return { dataInicio: fmtISO(ini), dataFim: fim };
}

export default function Relatorios() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [chamadas, setChamadas] = useState<any[]>([]);
  const [opcoes, setOpcoes] = useState<Opcoes>({ turmas: [], turnos: [], semestres: [] });

  const [filtros, setFiltros] = useState<Filtros>({});
  const [painelAberto, setPainelAberto] = useState(false);
  const [rascunho, setRascunho] = useState<Filtros>({});
  const [pickerAlvo, setPickerAlvo] = useState<null | "inicio" | "fim">(null);

  const { showError } = useErrorToast();
  const [exportandoDoc, setExportandoDoc] = useState<null | "consolidado" | "frequencia">(null);

  const compartilharPdf = async (
    endpoint: string,
    nomeArquivo: string,
    titulo: string,
    doc: "consolidado" | "frequencia"
  ) => {
    if (exportandoDoc) return;
    setExportandoDoc(doc);
    try {
      const uri = await apiDownload(endpoint, nomeArquivo);
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(uri, {
          mimeType: "application/pdf",
          UTI: "com.adobe.pdf",
          dialogTitle: titulo,
        });
      } else {
        showError("Compartilhamento indisponível neste dispositivo.");
      }
    } catch (err: any) {
      showError(err, "Não foi possível gerar o PDF.");
    } finally {
      setExportandoDoc(null);
    }
  };

  const exportarConsolidado = () => {
    const query = buildQuery(filtros);
    return compartilharPdf(
      `/professor/relatorios/chamadas${query}${query ? "&" : "?"}formato=pdf`,
      "consolidado-chamadas.pdf",
      "Consolidado de chamadas",
      "consolidado"
    );
  };

  // Aceita um alvo explícito (usado pelo botão do painel, que passa o rascunho
  // recém-aplicado) para não depender do estado `filtros` — que ainda não teria
  // sido atualizado pelo setFiltros(rascunho) no momento em que o setTimeout
  // dispara, por causa de closures (o setTimeout guarda a função desta
  // renderização, não a mais recente).
  const exportarFrequencia = (alvo: Filtros = filtros) => {
    if (!alvo.turmaId) {
      showError("Selecione uma turma no filtro para gerar a frequência.");
      return;
    }
    const turma = opcoes.turmas.find((t) => t.turma_id === alvo.turmaId);
    const p = new URLSearchParams({ formato: "pdf" });
    if (alvo.dataInicio) p.append("data_inicio", alvo.dataInicio);
    if (alvo.dataFim) p.append("data_fim", alvo.dataFim);
    return compartilharPdf(
      `/professor/relatorios/turmas/${alvo.turmaId}/frequencia?${p.toString()}`,
      `frequencia-${turma?.codigo_turma || "turma"}.pdf`,
      "Frequência por aluno",
      "frequencia"
    );
  };

  const loadRelatorios = async (f: Filtros) => {
    setLoading(true);
    try {
      const data = await apiGet(`/professor/relatorios/chamadas${buildQuery(f)}`);
      setChamadas(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Erro ao carregar relatórios:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadOpcoes = async () => {
    try {
      const data = await apiGet("/professor/relatorios/filtros");
      setOpcoes({
        turmas: data?.turmas ?? [],
        turnos: data?.turnos ?? [],
        semestres: data?.semestres ?? [],
      });
    } catch (err) {
      console.error("Erro ao carregar opções de filtro:", err);
    }
  };

  // Recarrega opções a cada foco da tela.
  useFocusEffect(
    useCallback(() => {
      loadOpcoes();
    }, [])
  );

  // Recarrega a lista ao focar a tela e sempre que os filtros mudam
  // (preserva o refresh-no-foco: chamadas recém-encerradas aparecem ao voltar).
  useFocusEffect(
    useCallback(() => {
      loadRelatorios(filtros);
    }, [filtros])
  );

  const abrirPainel = () => {
    setRascunho(filtros);
    setPainelAberto(true);
  };

  const aplicar = () => {
    setFiltros(rascunho);
    setPainelAberto(false);
  };

  const limpar = () => setRascunho({});

  const removerChip = (chave: "periodo" | "turma" | "turno" | "semestre") => {
    const next: Filtros = { ...filtros };
    if (chave === "periodo") {
      delete next.dataInicio;
      delete next.dataFim;
    } else if (chave === "turma") {
      delete next.turmaId;
    } else if (chave === "turno") {
      delete next.turno;
    } else if (chave === "semestre") {
      delete next.semestre;
    }
    setFiltros(next);
  };

  const aplicarPreset = (p: Preset) => {
    const { dataInicio, dataFim } = calcPreset(p);
    setRascunho((r) => ({ ...r, dataInicio, dataFim }));
  };

  const onPickerChange = (_event: any, selected?: Date) => {
    const alvo = pickerAlvo;
    setPickerAlvo(null);
    if (!selected || !alvo) return;
    const iso = fmtISO(selected);
    setRascunho((r) => (alvo === "inicio" ? { ...r, dataInicio: iso } : { ...r, dataFim: iso }));
  };

  const ativos = contarAtivos(filtros);
  const turmaSelecionada = opcoes.turmas.find((t) => t.turma_id === filtros.turmaId);
  const periodoLabel =
    filtros.dataInicio && filtros.dataFim
      ? filtros.dataInicio === filtros.dataFim
        ? fmtBR(filtros.dataInicio)
        : `${fmtBR(filtros.dataInicio)} – ${fmtBR(filtros.dataFim)}`
      : filtros.dataInicio
        ? `A partir de ${fmtBR(filtros.dataInicio)}`
        : filtros.dataFim
          ? `Até ${fmtBR(filtros.dataFim)}`
          : "";

  const menuItems: any[] = [
    { icon: "home-outline", activeIcon: "home", route: "/professor/home", label: "Início" },
    { icon: "clipboard-outline", activeIcon: "clipboard", route: "/professor/turmas", label: "Turmas" },
    { icon: "document-text-outline", activeIcon: "document-text", route: "/professor/relatorios", label: "Relatórios" },
    { icon: "person-outline", activeIcon: "person", route: "/professor/perfil", label: "Perfil" },
  ];

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <StatusBar barStyle="light-content" />

      <View style={styles.header}>
        <Text style={styles.headerTitle}>Relatórios</Text>
        <Text style={styles.headerSubtitle}>Histórico imutável de chamadas realizadas</Text>
      </View>

      <View style={styles.filterBar}>
        <TouchableOpacity
          style={styles.filterButton}
          onPress={abrirPainel}
          accessibilityRole="button"
          accessibilityLabel="Abrir filtros"
        >
          <Ionicons name="filter" size={18} color={Colors.brand.text} />
          <Text style={styles.filterButtonText}>Filtros</Text>
          {ativos > 0 && (
            <View style={styles.filterBadge}>
              <Text style={styles.filterBadgeText}>{ativos}</Text>
            </View>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.filterButton}
          onPress={exportarConsolidado}
          disabled={!!exportandoDoc}
          accessibilityRole="button"
          accessibilityLabel="Exportar consolidado em PDF"
        >
          {exportandoDoc === "consolidado" ? (
            <ActivityIndicator size="small" color={Colors.brand.text} />
          ) : (
            <Ionicons name="document-outline" size={18} color={Colors.brand.text} />
          )}
          <Text style={styles.filterButtonText}>PDF</Text>
        </TouchableOpacity>
      </View>

      {ativos > 0 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.chipsRow}
          contentContainerStyle={styles.chipsContent}
        >
          {periodoLabel ? (
            <ActiveChip label={periodoLabel} onRemove={() => removerChip("periodo")} />
          ) : null}
          {turmaSelecionada ? (
            <ActiveChip label={turmaSelecionada.nome_disciplina} onRemove={() => removerChip("turma")} />
          ) : null}
          {filtros.turno ? (
            <ActiveChip label={filtros.turno} onRemove={() => removerChip("turno")} />
          ) : null}
          {filtros.semestre ? (
            <ActiveChip label={filtros.semestre} onRemove={() => removerChip("semestre")} />
          ) : null}
        </ScrollView>
      )}

      {exportandoDoc === "frequencia" && (
        <View style={styles.exportBanner}>
          <ActivityIndicator size="small" color={Colors.brand.primary} />
          <Text style={styles.exportBannerText}>Gerando PDF de frequência…</Text>
        </View>
      )}

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.brand.primary} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          {chamadas.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Ionicons name="document-text-outline" size={48} color={Colors.brand.textSecondary} />
              <Text style={styles.emptyTitle}>
                {ativos > 0 ? "Nenhum relatório com esses filtros" : "Nenhuma chamada realizada"}
              </Text>
              <Text style={styles.emptyText}>
                {ativos > 0
                  ? "Ajuste ou limpe os filtros para ver mais resultados."
                  : "Suas chamadas encerradas aparecerão aqui."}
              </Text>
              {ativos > 0 && (
                <TouchableOpacity style={styles.clearInline} onPress={() => setFiltros({})}>
                  <Text style={styles.clearInlineText}>Limpar filtros</Text>
                </TouchableOpacity>
              )}
            </View>
          ) : (
            chamadas.map((c) => (
              <TouchableOpacity
                key={c.chamada_id}
                style={styles.card}
                activeOpacity={0.75}
                accessibilityRole="button"
                accessibilityLabel={`Ver relatório de ${c.nome_disciplina}`}
                onPress={() =>
                  router.push({
                    pathname: "/professor/relatorio-detalhe",
                    params: { chamada_id: c.chamada_id, turma_nome: c.nome_disciplina },
                  })
                }
              >
                <View style={styles.cardTop}>
                  <View style={styles.disciplinaInfo}>
                    <Text style={styles.disciplinaNome} numberOfLines={1}>
                      {c.nome_disciplina}
                    </Text>
                    <Text style={styles.disciplinaCodigo}>
                      {c.codigo_turma} • {c.data_chamada}
                    </Text>
                    <Text style={styles.disciplinaHorario}>
                      {c.horario_inicio} – {c.horario_fim}
                    </Text>
                  </View>
                  <View
                    style={[
                      styles.percentBadge,
                      {
                        backgroundColor:
                          c.percentual >= 75 ? "rgba(34,197,94,0.12)" : "rgba(255,75,75,0.12)",
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.percentText,
                        { color: c.percentual >= 75 ? "#22C55E" : Colors.brand.error },
                      ]}
                    >
                      {c.percentual}%
                    </Text>
                  </View>
                </View>

                <View style={styles.statsRow}>
                  <View style={styles.statItem}>
                    <Text style={styles.statValue}>{c.total_alunos}</Text>
                    <Text style={styles.statLabel}>Alunos</Text>
                  </View>
                  <View style={styles.statDivider} />
                  <View style={styles.statItem}>
                    <Text style={[styles.statValue, { color: "#22C55E" }]}>{c.presentes_alunos}</Text>
                    <Text style={styles.statLabel}>Presentes</Text>
                  </View>
                  <View style={styles.statDivider} />
                  <View style={styles.statItem}>
                    <Text style={[styles.statValue, { color: Colors.brand.error }]}>{c.ausentes_alunos}</Text>
                    <Text style={styles.statLabel}>Ausentes</Text>
                  </View>
                  <View style={styles.statDivider} />
                  <View style={styles.statItem}>
                    <Text style={[styles.statValue, { color: "#F59E0B" }]}>{c.parciais_alunos}</Text>
                    <Text style={styles.statLabel}>Parciais</Text>
                  </View>
                  <Ionicons
                    name="chevron-forward"
                    size={20}
                    color={Colors.brand.textSecondary}
                    style={{ marginLeft: "auto" }}
                  />
                </View>
              </TouchableOpacity>
            ))
          )}
          <View style={{ height: 120 }} />
        </ScrollView>
      )}

      <Modal
        visible={painelAberto}
        animationType="slide"
        transparent
        onRequestClose={() => setPainelAberto(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Filtros</Text>
              <TouchableOpacity onPress={() => setPainelAberto(false)} accessibilityLabel="Fechar filtros">
                <Ionicons name="close" size={24} color={Colors.brand.text} />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.sectionLabel}>Período</Text>
              <View style={styles.chipWrap}>
                {([
                  ["hoje", "Hoje"],
                  ["7dias", "7 dias"],
                  ["30dias", "30 dias"],
                  ["mes", "Este mês"],
                ] as [Preset, string][]).map(([key, label]) => (
                  <TouchableOpacity key={key} style={styles.choiceChip} onPress={() => aplicarPreset(key)}>
                    <Text style={styles.choiceChipText}>{label}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <View style={styles.dateRow}>
                <TouchableOpacity style={styles.dateField} onPress={() => setPickerAlvo("inicio")}>
                  <Text style={styles.dateFieldLabel}>De</Text>
                  <Text style={styles.dateFieldValue}>{fmtBR(rascunho.dataInicio) || "—"}</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.dateField} onPress={() => setPickerAlvo("fim")}>
                  <Text style={styles.dateFieldLabel}>Até</Text>
                  <Text style={styles.dateFieldValue}>{fmtBR(rascunho.dataFim) || "—"}</Text>
                </TouchableOpacity>
              </View>

              {pickerAlvo && (
                <DateTimePicker
                  value={
                    pickerAlvo === "inicio" && rascunho.dataInicio
                      ? new Date(rascunho.dataInicio)
                      : pickerAlvo === "fim" && rascunho.dataFim
                        ? new Date(rascunho.dataFim)
                        : new Date()
                  }
                  mode="date"
                  display={Platform.OS === "ios" ? "inline" : "default"}
                  onChange={onPickerChange}
                  themeVariant="dark"
                />
              )}

              {opcoes.turmas.length > 0 && (
                <>
                  <Text style={styles.sectionLabel}>Turma</Text>
                  <View style={styles.chipWrap}>
                    {opcoes.turmas.map((t) => {
                      const sel = rascunho.turmaId === t.turma_id;
                      return (
                        <TouchableOpacity
                          key={t.turma_id}
                          style={[styles.choiceChip, sel && styles.choiceChipActive]}
                          onPress={() =>
                            setRascunho((r) => ({
                              ...r,
                              turmaId: sel ? undefined : t.turma_id,
                            }))
                          }
                        >
                          <Text style={[styles.choiceChipText, sel && styles.choiceChipTextActive]}>
                            {t.nome_disciplina}
                          </Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                </>
              )}

              {opcoes.turnos.length > 0 && (
                <>
                  <Text style={styles.sectionLabel}>Turno</Text>
                  <View style={styles.chipWrap}>
                    {opcoes.turnos.map((tn) => {
                      const sel = rascunho.turno === tn;
                      return (
                        <TouchableOpacity
                          key={tn}
                          style={[styles.choiceChip, sel && styles.choiceChipActive]}
                          onPress={() =>
                            setRascunho((r) => ({
                              ...r,
                              turno: sel ? undefined : (tn as "Matutino" | "Noturno"),
                            }))
                          }
                        >
                          <Text style={[styles.choiceChipText, sel && styles.choiceChipTextActive]}>{tn}</Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                </>
              )}

              {opcoes.semestres.length > 0 && (
                <>
                  <Text style={styles.sectionLabel}>Semestre</Text>
                  <View style={styles.chipWrap}>
                    {opcoes.semestres.map((s) => {
                      const sel = rascunho.semestre === s;
                      return (
                        <TouchableOpacity
                          key={s}
                          style={[styles.choiceChip, sel && styles.choiceChipActive]}
                          onPress={() =>
                            setRascunho((r) => ({ ...r, semestre: sel ? undefined : s }))
                          }
                        >
                          <Text style={[styles.choiceChipText, sel && styles.choiceChipTextActive]}>{s}</Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                </>
              )}

              <View style={{ height: 16 }} />
            </ScrollView>

            <TouchableOpacity
              style={[
                styles.filterButton,
                styles.frequenciaButton,
                !rascunho.turmaId && { opacity: 0.4 },
              ]}
              onPress={() => {
                setPainelAberto(false);
                setFiltros(rascunho);
                setTimeout(() => exportarFrequencia(rascunho), 300);
              }}
              disabled={!rascunho.turmaId || !!exportandoDoc}
              accessibilityRole="button"
              accessibilityLabel="Exportar frequência por aluno em PDF"
            >
              <Ionicons name="people-outline" size={18} color={Colors.brand.text} />
              <Text style={styles.filterButtonText}>
                {rascunho.turmaId ? "Frequência da turma (PDF)" : "Selecione uma turma"}
              </Text>
            </TouchableOpacity>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.clearButton} onPress={limpar}>
                <Text style={styles.clearButtonText}>Limpar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.applyButton} onPress={aplicar}>
                <Text style={styles.applyButtonText}>Aplicar</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

function ActiveChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <View style={styles.activeChip}>
      <Text style={styles.activeChipText} numberOfLines={1}>
        {label}
      </Text>
      <TouchableOpacity onPress={onRemove} accessibilityLabel={`Remover filtro ${label}`}>
        <Ionicons name="close-circle" size={16} color={Colors.brand.textSecondary} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 16 },
  headerTitle: { color: Colors.brand.text, fontSize: 28, fontWeight: "800" },
  headerSubtitle: { color: Colors.brand.textSecondary, fontSize: 14, marginTop: 4 },

  filterBar: { paddingHorizontal: 24, paddingBottom: 8, flexDirection: "row", gap: 10 },
  filterButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.brand.card,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  filterButtonText: { color: Colors.brand.text, fontSize: 14, fontWeight: "700", marginLeft: 8 },
  frequenciaButton: { justifyContent: "center", marginTop: 12 },
  filterBadge: {
    marginLeft: 8,
    backgroundColor: Colors.brand.primary,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  filterBadgeText: { color: "#fff", fontSize: 12, fontWeight: "800" },

  exportBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginHorizontal: 24,
    marginBottom: 10,
    backgroundColor: Colors.brand.card,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  exportBannerText: { color: Colors.brand.text, fontSize: 13, fontWeight: "700" },

  chipsRow: { flexGrow: 0, flexShrink: 0, marginBottom: 4 },
  chipsContent: { paddingHorizontal: 24, gap: 8, alignItems: "center", paddingVertical: 4 },
  activeChip: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 14,
    paddingLeft: 12,
    paddingRight: 8,
    paddingVertical: 6,
    gap: 6,
    maxWidth: 220,
    flexShrink: 0,
    minHeight: 32,
  },
  activeChipText: { color: Colors.brand.text, fontSize: 13, fontWeight: "600", flexShrink: 1 },

  scrollContent: { paddingHorizontal: 24, paddingTop: 4 },
  card: {
    backgroundColor: Colors.brand.card,
    borderRadius: 24,
    padding: 20,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  cardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 },
  disciplinaInfo: { flex: 1, marginRight: 12 },
  disciplinaNome: { color: Colors.brand.text, fontSize: 17, fontWeight: "800" },
  disciplinaCodigo: { color: Colors.brand.textSecondary, fontSize: 13, marginTop: 4 },
  disciplinaHorario: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 2 },
  percentBadge: { borderRadius: 16, paddingHorizontal: 14, paddingVertical: 10, alignItems: "center", justifyContent: "center" },
  percentText: { fontSize: 18, fontWeight: "800" },
  statsRow: {
    flexDirection: "row",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.05)",
    paddingTop: 14,
  },
  statItem: { flex: 1, alignItems: "center" },
  statValue: { color: Colors.brand.text, fontSize: 18, fontWeight: "800" },
  statLabel: { color: Colors.brand.textSecondary, fontSize: 11, marginTop: 2 },
  statDivider: { width: 1, height: 28, backgroundColor: "rgba(255,255,255,0.06)" },

  emptyContainer: {
    alignItems: "center",
    paddingVertical: 60,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.07)",
    borderRadius: 24,
    borderStyle: "dashed",
  },
  emptyTitle: { color: Colors.brand.text, fontSize: 16, fontWeight: "700", marginTop: 14 },
  emptyText: { color: Colors.brand.textSecondary, fontSize: 13, marginTop: 6, textAlign: "center", paddingHorizontal: 24 },
  clearInline: {
    marginTop: 16,
    backgroundColor: Colors.brand.primary,
    borderRadius: 12,
    paddingHorizontal: 18,
    paddingVertical: 10,
  },
  clearInlineText: { color: "#fff", fontWeight: "700", fontSize: 13 },

  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "flex-end" },
  modalSheet: {
    backgroundColor: Colors.brand.background,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 28,
    maxHeight: "85%",
  },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  modalTitle: { color: Colors.brand.text, fontSize: 20, fontWeight: "800" },
  sectionLabel: { color: Colors.brand.textSecondary, fontSize: 13, fontWeight: "700", marginTop: 16, marginBottom: 8 },
  chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  choiceChip: {
    backgroundColor: Colors.brand.card,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  choiceChipActive: { backgroundColor: Colors.brand.primary, borderColor: Colors.brand.primary },
  choiceChipText: { color: Colors.brand.text, fontSize: 13, fontWeight: "600" },
  choiceChipTextActive: { color: "#fff" },
  dateRow: { flexDirection: "row", gap: 12, marginTop: 12 },
  dateField: {
    flex: 1,
    backgroundColor: Colors.brand.card,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  dateFieldLabel: { color: Colors.brand.textSecondary, fontSize: 11 },
  dateFieldValue: { color: Colors.brand.text, fontSize: 15, fontWeight: "700", marginTop: 2 },
  modalActions: { flexDirection: "row", gap: 12, marginTop: 16 },
  clearButton: {
    flex: 1,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
  },
  clearButtonText: { color: Colors.brand.text, fontWeight: "700", fontSize: 14 },
  applyButton: { flex: 2, borderRadius: 14, paddingVertical: 14, alignItems: "center", backgroundColor: Colors.brand.primary },
  applyButtonText: { color: "#fff", fontWeight: "800", fontSize: 14 },
});
