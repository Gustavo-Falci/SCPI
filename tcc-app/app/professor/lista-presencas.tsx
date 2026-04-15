import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useState, useEffect } from "react";
import { useLocalSearchParams } from "expo-router";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
  Alert,
} from "react-native";
import { apiGet, apiPost } from "../../services/api";

export default function ListaPresenca() {
  const { turma_id, turma_nome } = useLocalSearchParams();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [statusChamada, setStatusChamada] = useState<any>(null);
  const [alunos, setAlunos] = useState<any[]>([]);

  const carregarStatus = async () => {
    try {
      if (!turma_id) return;
      
      const statusResp = await apiGet(`/chamadas/status/${turma_id}`);
      setStatusChamada(statusResp);

      if (statusResp.status === "Aberta") {
         try {
             const listResp = await apiGet(`/chamadas/${statusResp.chamada_id}/alunos`);
             if(listResp && listResp.alunos){
                 setAlunos(listResp.alunos);
             }
         } catch(e) {
             console.log("Erro ao buscar alunos", e);
         }
      }

    } catch (err: any) {
      console.error("Erro ao carregar status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarStatus();
    const intervalId = setInterval(carregarStatus, 3000);
    return () => clearInterval(intervalId);
  }, [turma_id]);

  const fecharChamada = async () => {
    try {
        await apiPost(`/chamadas/fechar/${turma_id}`, {});
        Alert.alert("Sucesso", "Chamada encerrada e salva no histórico!");
        router.back();
    } catch(err: any) {
        Alert.alert("Erro", err.message || "Erro ao fechar chamada");
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Lista de presença</Text>
        <View style={{ width: 22 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.summaryCard}>
          <Text style={styles.classTitle}>{turma_nome || "Turma"}</Text>
          
          {loading ? (
              <ActivityIndicator color="#5B3EFF" />
          ) : (
              <>
                <Text style={{color: '#fff', marginBottom: 10}}>
                    Status: {statusChamada?.status || 'Desconhecido'}
                </Text>
                <View style={styles.summaryRow}>
                  <Text style={{color: '#fff'}}>👥 {statusChamada?.total_alunos || 0} alunos</Text>
                  <Text style={styles.present}>✅ {statusChamada?.presentes || 0} presentes</Text>
                  <Text style={styles.absent}>❌ {statusChamada?.ausentes || 0} ausentes</Text>
                </View>
              </>
          )}
        </View>
        
        {statusChamada?.status === "Aberta" && (
           <TouchableOpacity 
              style={{backgroundColor: '#EF4444', marginHorizontal: 20, padding: 15, borderRadius: 10, alignItems: 'center', marginBottom: 20}}
              onPress={fecharChamada}
           >
               <Text style={{color: '#fff', fontWeight: 'bold', fontSize: 16}}>Encerrar Chamada e Salvar</Text>
           </TouchableOpacity>
        )}

        {alunos.length > 0 ? alunos.map((aluno) => (
          <View style={styles.studentCard} key={aluno.id}>
            <Text style={styles.studentName}>{aluno.nome}</Text>

            <View
              style={[
                styles.statusButton,
                aluno.presente ? styles.presentBtn : styles.absentBtn,
              ]}
            >
              <Text style={styles.statusText}>
                {aluno.presente ? "Presente" : "Ausente"}
              </Text>
            </View>
          </View>
        )) : (
            <Text style={{textAlign: 'center', color: '#888', marginTop: 20, paddingHorizontal: 20}}>
               {statusChamada?.status === "Aberta" ? "Aguardando dados..." : "Não há chamada aberta."}
            </Text>
        )}

        <View style={{ height: 120 }} />
      </ScrollView>

      <View style={styles.bottomMenu}>
        <TouchableOpacity onPress={() => router.replace("/professor/home")}>
          <Ionicons name="home-outline" size={22} color="#aaa" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/professor/turmas")}>
          <Ionicons name="clipboard-outline" size={22} color="#7C4DFF" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/professor/horarios-turmas")}>
          <Ionicons name="calendar-outline" size={22} color="#aaa" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/professor/perfil")}>
          <Ionicons name="person-outline" size={22} color="#aaa" />
        </TouchableOpacity>
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
  headerTitle: { color: "#fff", fontSize: 18, fontWeight: "700" },
  summaryCard: { backgroundColor: "#111", margin: 20, borderRadius: 16, padding: 16 },
  classTitle: { color: "#fff", fontSize: 16, fontWeight: "700", marginBottom: 10 },
  summaryRow: { flexDirection: "row", justifyContent: "space-between" },
  present: { color: "#22C55E", fontWeight: "600" },
  absent: { color: "#EF4444", fontWeight: "600" },
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
  studentName: { color: "#fff", fontSize: 14 },
  statusButton: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20 },
  presentBtn: { backgroundColor: "#22C55E" },
  absentBtn: { backgroundColor: "#EF4444" },
  statusText: { color: "#fff", fontSize: 12, fontWeight: "600" },
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
