import React, { useState, useCallback, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StatusBar,
  Modal,
  Platform,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useFocusEffect } from "expo-router";
import DateTimePicker from "@react-native-community/datetimepicker";
import * as Sharing from "expo-sharing";
import * as Haptics from "expo-haptics";

import { apiGet, apiDownload } from "../../services/api";
import { RelatorioCard } from "../../components/relatorios/relatorio-card";
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

const PAGE_SIZE = 20;

// `paginacao` é opcional porque a mesma função monta a query do PDF, que é o
// documento do recorte inteiro e não pode receber limit/offset.
function buildQuery(f: Filtros, paginacao?: { offset: number }): string {
  const p = new URLSearchParams();
  if (f.dataInicio) p.append("data_inicio", f.dataInicio);
  if (f.dataFim) p.append("data_fim", f.dataFim);
  if (f.turmaId) p.append("turma_id", f.turmaId);
  if (f.turno) p.append("turno", f.turno);
  if (f.semestre) p.append("semestre", f.semestre);
  if (paginacao) {
    p.append("paginado", "1");
    p.append("limit", String(PAGE_SIZE));
    p.append("offset", String(paginacao.offset));
  }
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
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [temMais, setTemMais] = useState(false);
  const [total, setTotal] = useState(0);
  const requisicaoRef = useRef(0);
  const insets = useSafeAreaInsets();

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

  // Normaliza as duas formas de resposta: envelope (backend novo) e array puro
  // (backend antigo ignora `paginado` e devolve a lista como sempre).
  const extrair = (data: any) =>
    Array.isArray(data)
      ? { items: data, total: data.length, has_more: false }
      : { items: data?.items ?? [], total: data?.total ?? 0, has_more: !!data?.has_more };

  const loadRelatorios = async (f: Filtros) => {
    const token = ++requisicaoRef.current;
    setLoading(true);
    try {
      const data = await apiGet(`/professor/relatorios/chamadas${buildQuery(f, { offset: 0 })}`);
      if (token !== requisicaoRef.current) return;
      const { items, total: t, has_more } = extrair(data);
      setChamadas(items);
      setTotal(t);
      setTemMais(has_more);
    } catch (err) {
      if (token !== requisicaoRef.current) return;
      console.error("Erro ao carregar relatórios:", err);
    } finally {
      if (token === requisicaoRef.current) setLoading(false);
    }
  };

  const carregarMais = async () => {
    if (carregandoMais || loading || !temMais) return;
    const token = requisicaoRef.current;
    setCarregandoMais(true);
    try {
      const data = await apiGet(
        `/professor/relatorios/chamadas${buildQuery(filtros, { offset: chamadas.length })}`
      );
      // Filtro trocado no meio do caminho: descartar, senão a página antiga é
      // acrescentada em cima de uma lista que já é de outro recorte.
      if (token !== requisicaoRef.current) return;
      const { items, has_more } = extrair(data);
      setChamadas((atuais) => [...atuais, ...items]);
      setTemMais(has_more);
    } catch (err) {
      if (token !== requisicaoRef.current) return;
      console.error("Erro ao carregar mais relatórios:", err);
      setTemMais(false);
    } finally {
      if (token === requisicaoRef.current) setCarregandoMais(false);
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
        <Text style={styles.headerSubtitle}>
          {total > 0
            ? `${total} ${total === 1 ? "chamada realizada" : "chamadas realizadas"}`
            : "Histórico imutável de chamadas realizadas"}
        </Text>
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
        <FlatList
          data={chamadas}
          keyExtractor={(c) => String(c.chamada_id)}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
          onEndReached={carregarMais}
          onEndReachedThreshold={0.5}
          renderItem={({ item }) => (
            <RelatorioCard
              chamada={item}
              onPress={() =>
                router.push({
                  pathname: "/professor/relatorio-detalhe",
                  params: { chamada_id: item.chamada_id, turma_nome: item.nome_disciplina },
                })
              }
            />
          )}
          ListEmptyComponent={
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
          }
          ListFooterComponent={
            <>
              {carregandoMais && (
                <ActivityIndicator
                  size="small"
                  color={Colors.brand.primary}
                  style={{ marginVertical: 16 }}
                />
              )}
              {/* Respiro do FloatingMenu: sem isso o último card fica atrás dele. */}
              <View style={{ height: 120 }} />
            </>
          }
        />
      )}

      <Modal
        visible={painelAberto}
        animationType="slide"
        transparent
        onRequestClose={() => setPainelAberto(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalSheet, { paddingBottom: Math.max(insets.bottom, 28) }]}>
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
  // paddingBottom vai inline no componente: precisa do inset da barra de
  // navegação (Modal renderiza fora da hierarquia do SafeAreaView, então não
  // herda nada) e StyleSheet.create é estático.
  modalSheet: {
    backgroundColor: Colors.brand.background,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    paddingHorizontal: 24,
    paddingTop: 20,
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
