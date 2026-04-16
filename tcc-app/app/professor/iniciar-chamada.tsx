import React, { useEffect, useState, useCallback } from "react";
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
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter, useFocusEffect } from "expo-router";

import { apiGet, apiPost } from "../../services/api";
import { storage } from "../../services/storage";
import { Colors } from "../../constants/theme";

export default function IniciarChamada() {
  const router = useRouter();
  const [turmas, setTurmas] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadTurmas = async () => {
    try {
      const userId = await storage.getItem("user_id");
      if (!userId) return;
      const response = await apiGet(`/turmas/${userId}`);
      setTurmas(response.turmas || []);
    } catch (err: any) {
      console.error("Erro carregar turmas:", err);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadTurmas();
    }, [])
  );

  const handleAbrirChamada = async (turmaId: string, nomeTurma: string, podeIniciar: boolean) => {
    if (!podeIniciar) {
      Alert.alert("Acesso Negado", "Você só pode iniciar a chamada durante o horário oficial da aula.");
      return;
    }

    try {
      setLoading(true);
      await apiPost("/chamadas/abrir", { turma_id: turmaId });
      
      Alert.alert("Sucesso!", `Chamada biométrica iniciada para: ${nomeTurma}`);
      
      router.replace({
        pathname: "/professor/lista-presencas",
        params: { turma_id: turmaId, turma_nome: nomeTurma },
      });
    } catch (err: any) {
      Alert.alert("Erro", err.message || "Falha ao abrir a chamada.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Iniciar Frequência</Text>
        <View style={{ width: 44 }} />
      </View>

      <View style={styles.infoBox}>
        <Ionicons name="time-outline" size={20} color={Colors.brand.primary} />
        <Text style={styles.infoText}>As chamadas só podem ser iniciadas dentro do período de aula estabelecido na grade horária.</Text>
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {loading && turmas.length === 0 ? (
          <ActivityIndicator size="large" color={Colors.brand.primary} style={{ marginTop: 40 }} />
        ) : (
          turmas.map((t: any) => (
            <TouchableOpacity 
              key={t.turma_id}
              style={[styles.card, !t.pode_iniciar && styles.cardDisabled]} 
              onPress={() => handleAbrirChamada(t.turma_id, t.nome_disciplina, t.pode_iniciar)}
              activeOpacity={t.pode_iniciar ? 0.7 : 1}
            >
              <View style={[styles.iconCircle, !t.pode_iniciar && styles.iconCircleDisabled]}>
                <MaterialCommunityIcons 
                  name={t.pode_iniciar ? "face-recognition" : "lock-outline"} 
                  size={24} 
                  color={t.pode_iniciar ? Colors.brand.primary : Colors.brand.textSecondary} 
                />
              </View>
              
              <View style={styles.cardContent}>
                <Text style={[styles.className, !t.pode_iniciar && styles.textDisabled]}>{t.nome_disciplina}</Text>
                <Text style={styles.classTime}>{t.proximo_horario}</Text>
              </View>

              {t.pode_iniciar ? (
                <Ionicons name="play-circle" size={32} color={Colors.brand.primary} />
              ) : (
                <View style={styles.lockedBadge}>
                  <Text style={styles.lockedText}>Bloqueado</Text>
                </View>
              )}
            </TouchableOpacity>
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
  infoBox: { flexDirection: 'row', gap: 12, backgroundColor: 'rgba(75, 57, 239, 0.05)', margin: 24, padding: 16, borderRadius: 16, borderWidth: 1, borderColor: 'rgba(75, 57, 239, 0.1)' },
  infoText: { flex: 1, color: Colors.brand.textSecondary, fontSize: 13, lineHeight: 18 },
  scrollContent: { paddingHorizontal: 24 },
  card: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.brand.card,
    padding: 16, borderRadius: 20, marginBottom: 12, borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  cardDisabled: {
    opacity: 0.6,
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
  },
  iconCircle: { width: 48, height: 48, borderRadius: 24, backgroundColor: 'rgba(75, 57, 239, 0.1)', justifyContent: 'center', alignItems: 'center', marginRight: 16 },
  iconCircleDisabled: { backgroundColor: 'rgba(255,255,255,0.05)' },
  cardContent: { flex: 1 },
  className: { color: "#fff", fontSize: 16, fontWeight: "700" },
  classTime: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 4 },
  textDisabled: { color: Colors.brand.textSecondary },
  lockedBadge: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  lockedText: {
    color: Colors.brand.textSecondary,
    fontSize: 10,
    fontWeight: '800',
    textTransform: 'uppercase',
  }
});
