import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useLocalSearchParams } from "expo-router";

import { apiGet } from "../../services/api";
import { Colors } from "../../constants/theme";

export default function DetalhesTurma() {
  const { turma_id, turma_nome } = useLocalSearchParams();
  const router = useRouter();
  const [alunos, setAlunos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAlunos() {
      try {
        const response = await apiGet(`/turmas/${turma_id}/alunos`);
        setAlunos(response.alunos || []);
      } catch (err: any) {
        console.error("Erro ao carregar alunos:", err);
      } finally {
        setLoading(false);
      }
    }
    loadAlunos();
  }, [turma_id]);

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Alunos Matriculados</Text>
        <View style={{ width: 44 }} />
      </View>

      <View style={styles.classBanner}>
        <Text style={styles.className}>{turma_nome}</Text>
        <Text style={styles.classCount}>{alunos.length} Alunos na turma</Text>
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {loading ? (
          <ActivityIndicator size="large" color={Colors.brand.primary} style={{ marginTop: 40 }} />
        ) : alunos.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="people-outline" size={50} color={Colors.brand.textSecondary} />
            <Text style={styles.emptyText}>Nenhum aluno matriculado nesta turma.</Text>
          </View>
        ) : (
          alunos.map((aluno) => (
            <View style={styles.studentCard} key={aluno.id}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{aluno.nome.charAt(0)}</Text>
              </View>
              <View style={styles.studentInfo}>
                <Text style={styles.studentName}>{aluno.nome}</Text>
                <Text style={styles.studentRA}>RA: {aluno.ra}</Text>
              </View>
              <Ionicons name="mail-outline" size={18} color={Colors.brand.textSecondary} />
            </View>
          ))
        )}
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, height: 60 },
  headerTitle: { fontSize: 18, fontWeight: "800", color: "#fff" },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.brand.card, justifyContent: "center", alignItems: "center" },
  classBanner: { padding: 24, backgroundColor: Colors.brand.card, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.05)' },
  className: { color: '#fff', fontSize: 22, fontWeight: '800' },
  classCount: { color: Colors.brand.textSecondary, fontSize: 14, marginTop: 4 },
  scrollContent: { paddingHorizontal: 24, paddingTop: 20 },
  studentCard: {
    flexDirection: "row", alignItems: "center", backgroundColor: Colors.brand.card,
    padding: 16, borderRadius: 20, marginBottom: 12, borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  avatar: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(75, 57, 239, 0.1)', justifyContent: "center", alignItems: "center", marginRight: 16 },
  avatarText: { color: Colors.brand.primary, fontWeight: "800", fontSize: 16 },
  studentInfo: { flex: 1 },
  studentName: { color: "#fff", fontSize: 15, fontWeight: "600" },
  studentRA: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 2 },
  emptyContainer: { alignItems: "center", paddingVertical: 60 },
  emptyText: { color: Colors.brand.textSecondary, fontSize: 16, marginTop: 16, textAlign: 'center' },
});
