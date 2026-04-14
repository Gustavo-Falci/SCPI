import { Feather, Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../services/api";
import {
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  Alert,
  ActivityIndicator
} from "react-native";
import { storage } from "../../services/storage";



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
        const userId = await storage.getItem("user_id"); // Precisamos salvar no login ou extrair do token
        // Como o auth/login no FastAPI n�o retorna o user_id, vamos usar a rota chamando /turmas/{user_id} 
        // Para simplificar no teste, usaremos o ID do profTeste conhecido
        if (!userId) {
          Alert.alert("Erro", "Usuário não identificado.");
          router.replace("/auth/login");
          return;
        }
        
        const response = await apiGet(`/turmas/${userId}`);
        setTurmas(response.turmas || []);
      } catch (err: any) {
        console.log("Erro carregar turmas", err.message);
      } finally {
        setLoading(false);
      }
    }
    loadTurmas();
  }, []);

  const abrirChamada = async (turmaId: string, nomeTurma: string) => {
    try {
      const resp = await apiPost("/chamadas/abrir", { turma_id: turmaId });
      Alert.alert("Sucesso!", `Chamada aberta para a turma: ${nomeTurma}`);
      
      router.push({
        pathname: "/professor/lista-presencas",
        params: { turma_id: turmaId, turma_nome: nomeTurma },
      });
    } catch (err: any) {
      Alert.alert("Erro", err.message || "Falha ao abrir a chamada.");
    }
  };

  return (
    <View style={styles.container}>
      {/* HEADER */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={22} color="#fff" />
          </TouchableOpacity>

          <Text style={styles.headerTitle}>Minhas turmas</Text>
        </View>

        <Ionicons name="notifications-outline" size={22} color="#fff" />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.searchBox}>
          <Ionicons name="search-outline" size={18} color="#9CA3AF" />
          <TextInput
            placeholder="Buscar turmas..."
            placeholderTextColor="#9CA3AF"
            style={styles.input}
            value={search}
            onChangeText={setSearch}
          />
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Turmas Cadastradas</Text>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color="#5B3EFF" style={{ marginTop: 20 }} />
        ) : turmasFiltradas.length === 0 ? (
          <Text style={{ textAlign: 'center', color: '#9CA3AF', marginTop: 20 }}>Nenhuma turma encontrada.</Text>
        ) : (
          turmasFiltradas.map((t: any) => (
            <View style={styles.card} key={t.turma_id}>
              <View style={styles.cardHeader}>
                <Text style={styles.className}>{t.nome_disciplina}</Text>

                <View style={styles.time}>
                  <Ionicons name="time-outline" size={14} color="#5B3EFF" />
                  <Text style={styles.timeText}>{t.codigo_turma}</Text>
                </View>
              </View>

              <Text style={styles.classInfo}>ID Interno: {t.turma_id.split("-")[0]}</Text>

              <TouchableOpacity
                style={styles.button}
                onPress={() => abrirChamada(t.turma_id, t.nome_disciplina)}
              >
                <Feather name="video" size={16} color="#5B3EFF" />
                <Text style={styles.buttonText}>Abrir Chamada (C�mera Ativa)</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={[styles.button, { marginTop: 10, backgroundColor: 'transparent', borderWidth: 1, borderColor: '#5B3EFF' }]}
                onPress={() =>
                  router.push({
                    pathname: "/professor/lista-presencas",
                    params: { turma_id: t.turma_id, turma_nome: t.nome_disciplina },
                  })
                }
              >
                <Feather name="list" size={16} color="#5B3EFF" />
                <Text style={[styles.buttonText, { color: '#5B3EFF' }]}>Ver Presen�as (Status)</Text>
              </TouchableOpacity>
            </View>
          ))
        )}

        <View style={{ height: 100 }} />
      </ScrollView>

      <View style={styles.bottomMenu}>
        <Ionicons name="home-outline" size={22} color="#aaa" />
        <Ionicons name="clipboard-outline" size={22} color="#7C4DFF" />
        <Ionicons name="calendar-outline" size={22} color="#aaa" />
        <Ionicons name="person-outline" size={22} color="#aaa" />
      </View>
    </View>
  );
}


const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#E9EAEC",
  },

  header: {
    backgroundColor: "#5B3EFF",
    paddingTop: 60,
    paddingBottom: 25,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottomLeftRadius: 25,
    borderBottomRightRadius: 25,
  },

  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },

  headerTitle: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "700",
  },

  searchBox: {
    marginTop: 20,
    marginHorizontal: 20,
    backgroundColor: "#F3F4F6",
    borderRadius: 12,
    height: 44,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
  },

  input: {
    marginLeft: 8,
    flex: 1,
    fontSize: 14,
  },

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginHorizontal: 20,
    marginTop: 30,
    marginBottom: 20,
  },

  sectionTitle: {
    fontSize: 28,
    fontWeight: "600",
  },

  day: {
    color: "#6B7280",
    fontSize: 13,
  },

  card: {
    backgroundColor: "#111",
    marginHorizontal: 20,
    marginTop: 14,
    borderRadius: 16,
    padding: 16,
  },

  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  className: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },

  classInfo: {
    color: "#9CA3AF",
    marginTop: 4,
    marginBottom: 12,
  },

  time: {
    backgroundColor: "#EEF2FF",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },

  timeText: {
    marginLeft: 4,
    fontSize: 12,
    color: "#5B3EFF",
    fontWeight: "600",
  },

  button: {
    backgroundColor: "#F3F4F6",
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },

  buttonText: {
    marginLeft: 6,
    color: "#5B3EFF",
    fontSize: 13,
    fontWeight: "500",
  },

  bottomMenu: {
    position: "absolute",
    bottom: 15,
    left: 15,
    right: 15,
    height: 65,
    backgroundColor: "#111",
    borderRadius: 20,
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
  },
});