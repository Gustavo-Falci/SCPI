import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { useLocalSearchParams } from "expo-router";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

export default function ListaPresenca() {
  const { turma } = useLocalSearchParams();
  const router = useRouter();

  const [alunos, setAlunos] = useState([
    { id: 1, nome: "Marcos da Silva", presente: true },
    { id: 2, nome: "Maria Clara", presente: false },
    { id: 3, nome: "Carlos Lima", presente: false },
    { id: 4, nome: "Fernanda Alves", presente: true },
    { id: 5, nome: "João Pedro", presente: false },
    { id: 6, nome: "Gustavo Falci", presente: true },
    { id: 7, nome: "Pedro Oliveira", presente: true },
    { id: 8, nome: "Bruno Augusto", presente: true },
  ]);

  const togglePresenca = (id: number) => {
    setAlunos((prev) =>
      prev.map((aluno) =>
        aluno.id === id
          ? { ...aluno, presente: !aluno.presente }
          : aluno
      )
    );
  };

  const presentes = alunos.filter((a) => a.presente).length;
  const ausentes = alunos.length - presentes;

  return (
    <View style={styles.container}>
      {/* HEADER */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>

        <Text style={styles.headerTitle}>Lista de presença</Text>

        <View style={{ width: 22 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* RESUMO */}
        <View style={styles.summaryCard}>
          <Text style={styles.classTitle}>{turma}</Text>

          <View style={styles.summaryRow}>
            <Text style={styles.present}>
              ✅ {presentes} presentes
            </Text>
            <Text style={styles.absent}>
              ❌ {ausentes} ausentes
            </Text>
          </View>
        </View>

        {/* LISTA */}
        {alunos.map((aluno) => (
          <View style={styles.studentCard} key={aluno.id}>
            <Text style={styles.studentName}>{aluno.nome}</Text>

            <TouchableOpacity
              style={[
                styles.statusButton,
                aluno.presente ? styles.presentBtn : styles.absentBtn,
              ]}
              onPress={() => togglePresenca(aluno.id)}
            >
              <Text style={styles.statusText}>
                {aluno.presente ? "Presente" : "Ausente"}
              </Text>
            </TouchableOpacity>
          </View>
        ))}

        <View style={{ height: 120 }} />
      </ScrollView>

      {/* MENU */}
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
  container: { flex: 1, backgroundColor: "#E9EAEC" },

  header: {
    backgroundColor: "#5B3EFF",
    paddingTop: 60,
    paddingBottom: 25,
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomLeftRadius: 25,
    borderBottomRightRadius: 25,
  },

  headerTitle: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },

  summaryCard: {
    backgroundColor: "#111",
    margin: 20,
    borderRadius: 16,
    padding: 16,
  },

  classTitle: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 10,
  },

  summaryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  present: {
    color: "#22C55E",
    fontWeight: "600",
  },

  absent: {
    color: "#EF4444",
    fontWeight: "600",
  },

  studentCard: {
    backgroundColor: "#111",
    marginHorizontal: 20,
    marginBottom: 14,
    borderRadius: 14,
    padding: 16,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  studentName: {
    color: "#fff",
    fontSize: 14,
  },

  statusButton: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
  },

  presentBtn: {
    backgroundColor: "#22C55E",
  },

  absentBtn: {
    backgroundColor: "#EF4444",
  },

  statusText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
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