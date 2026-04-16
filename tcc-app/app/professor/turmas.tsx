import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Feather, Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { apiGet, apiPost } from "../../services/api";
import { storage } from "../../services/storage";
import { Colors } from "../../constants/theme";
import { Input } from "../../components/ui/input";
import { FloatingMenu } from "../../components/layout/floating-menu";

export default function Turmas() {
  const router = useRouter();
  const [turmas, setTurmas] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const turmasFiltradas = turmas.filter(t =>
    t.nome_disciplina.toLowerCase().includes(search.toLowerCase()) ||
    t.codigo_turma.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    async function loadTurmas() {
      try {
        const userId = await storage.getItem("user_id");
        if (!userId) {
          router.replace("/auth/login");
          return;
        }
        const response = await apiGet(`/turmas/${userId}`);
        setTurmas(response.turmas || []);
      } catch (err: any) {
        console.error("Erro carregar turmas:", err.message);
      } finally {
        setLoading(false);
      }
    }
    loadTurmas();
  }, []);

  const abrirChamada = async (turmaId: string, nomeTurma: string) => {
    try {
      await apiPost("/chamadas/abrir", { turma_id: turmaId });
      Alert.alert("Sucesso!", `Chamada aberta para a turma: ${nomeTurma}`);
      
      router.push({
        pathname: "/professor/lista-presencas",
        params: { turma_id: turmaId, turma_nome: nomeTurma },
      });
    } catch (err: any) {
      Alert.alert("Erro", err.message || "Falha ao abrir a chamada.");
    }
  };

  const menuItems: any[] = [
    { icon: 'home-outline', activeIcon: 'home', route: '/professor/home' },
    { icon: 'clipboard-outline', activeIcon: 'clipboard', route: '/professor/turmas' },
    { icon: 'calendar-outline', activeIcon: 'calendar', route: '/professor/horarios-turmas' },
    { icon: 'person-outline', activeIcon: 'person', route: '/professor/perfil' },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" />
      
      {/* HEADER PERSONALIZADO */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Minhas Turmas</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* BUSCA */}
        <Input
          placeholder="Buscar disciplina ou código..."
          value={search}
          onChangeText={setSearch}
          icon="search-outline"
          containerStyle={styles.searchContainer}
        />

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Turmas ativas</Text>
          <Text style={styles.countText}>{turmasFiltradas.length} turmas</Text>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color={Colors.brand.primary} style={{ marginTop: 40 }} />
        ) : turmasFiltradas.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="search" size={50} color={Colors.brand.textSecondary} />
            <Text style={styles.emptyText}>Nenhuma turma encontrada.</Text>
          </View>
        ) : (
          turmasFiltradas.map((t: any) => (
            <View style={styles.card} key={t.turma_id}>
              <View style={styles.cardInfo}>
                <Text style={styles.className}>{t.nome_disciplina}</Text>
                <View style={styles.codeRow}>
                   <Ionicons name="barcode-outline" size={14} color={Colors.brand.textSecondary} />
                   <Text style={styles.codeText}>{t.codigo_turma}</Text>
                </View>
              </View>

              <View style={styles.actionRow}>
                <TouchableOpacity
                  style={styles.primaryAction}
                  onPress={() => abrirChamada(t.turma_id, t.nome_disciplina)}
                >
                  <Ionicons name="camera-outline" size={18} color="#fff" />
                  <Text style={styles.primaryActionText}>Abrir Chamada</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.secondaryAction}
                  onPress={() =>
                    router.push({
                      pathname: "/professor/lista-presencas",
                      params: { turma_id: t.turma_id, turma_nome: t.nome_disciplina },
                    })
                  }
                >
                  <Ionicons name="list-outline" size={18} color={Colors.brand.primary} />
                </TouchableOpacity>
              </View>
            </View>
          ))
        )}

        <View style={{ height: 120 }} />
      </ScrollView>

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.brand.background,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    height: 60,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#fff",
  },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.brand.card,
    justifyContent: "center",
    alignItems: "center",
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 10,
  },
  searchContainer: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    marginBottom: 16,
    paddingHorizontal: 4,
  },
  sectionTitle: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "800",
  },
  countText: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
    marginBottom: 4,
  },
  card: {
    backgroundColor: Colors.brand.card,
    borderRadius: 24,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  cardInfo: {
    marginBottom: 16,
  },
  className: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },
  codeRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 6,
    gap: 6,
  },
  codeText: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
  },
  actionRow: {
    flexDirection: "row",
    gap: 12,
  },
  primaryAction: {
    flex: 1,
    backgroundColor: Colors.brand.primary,
    height: 48,
    borderRadius: 14,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },
  primaryActionText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "700",
  },
  secondaryAction: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: "rgba(75, 57, 239, 0.1)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(75, 57, 239, 0.2)",
  },
  emptyContainer: {
    alignItems: "center",
    paddingVertical: 60,
  },
  emptyText: {
    color: Colors.brand.textSecondary,
    fontSize: 16,
    marginTop: 16,
  },
});
