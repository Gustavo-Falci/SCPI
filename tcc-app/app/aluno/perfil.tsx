import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { storage } from "../../services/storage";
import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";
import { Button } from "../../components/ui/button";

export default function PerfilAluno() {
  const router = useRouter();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [ra, setRa] = useState("");

  useEffect(() => {
    const loadUser = async () => {
      const userName = await storage.getItem("user_name");
      const userEmail = await storage.getItem("user_email");
      const userRa = await storage.getItem("user_ra");
      setNome(userName || "Aluno");
      setEmail(userEmail || "aluno@exemplo.com");
      setRa(userRa || "000000");
    };
    loadUser();
  }, []);

  const handleLogout = async () => {
    await storage.clear();
    router.replace("/auth/login");
  };

  const menuItems: any[] = [
    { icon: 'home-outline', activeIcon: 'home', route: '/aluno/home', label: 'Início' },
    { icon: 'stats-chart-outline', activeIcon: 'stats-chart', route: '/aluno/frequencia', label: 'Frequência' },
    { icon: 'calendar-outline', activeIcon: 'calendar', route: '/aluno/horarios', label: 'Horários' },
    { icon: 'person-outline', activeIcon: 'person', route: '/aluno/perfil', label: 'Perfil' },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Meu Perfil</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.profileCard}>
          <View style={[styles.avatarGradient, { backgroundColor: Colors.brand.primary }]}>
            <Ionicons name="school" size={50} color="#fff" />
          </View>
          
          <Text style={styles.nameText}>{nome}</Text>
          <Text style={styles.emailText}>{email}</Text>
          
          <View style={styles.roleBadge}>
            <Text style={styles.roleText}>ALUNO</Text>
          </View>
        </View>

        <View style={styles.infoSection}>
          <Text style={styles.sectionTitle}>Dados Acadêmicos</Text>
          
          <View style={styles.infoItem}>
            <View style={styles.iconBox}>
              <Ionicons name="id-card-outline" size={20} color={Colors.brand.primary} />
            </View>
            <View style={styles.infoTexts}>
              <Text style={styles.infoLabel}>Registro Acadêmico (RA/CPF)</Text>
              <Text style={styles.infoValue}>{ra}</Text>
            </View>
          </View>

          <View style={styles.infoItem}>
            <View style={styles.iconBox}>
              <Ionicons name="mail-outline" size={20} color={Colors.brand.primary} />
            </View>
            <View style={styles.infoTexts}>
              <Text style={styles.infoLabel}>E-mail Institucional</Text>
              <Text style={styles.infoValue}>{email}</Text>
            </View>
          </View>
        </View>

        <View style={styles.actionsSection}>
          <Button 
            title="Sair da Conta" 
            onPress={handleLogout} 
            variant="outline" 
            style={styles.logoutBtn}
            textStyle={{ color: Colors.brand.error }}
          />
        </View>

        <View style={{ height: 120 }} />
      </ScrollView>

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, height: 60 },
  headerTitle: { fontSize: 18, fontWeight: "800", color: "#fff" },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.brand.card, justifyContent: "center", alignItems: "center" },
  scrollContent: { paddingHorizontal: 24, paddingTop: 20 },
  profileCard: {
    backgroundColor: Colors.brand.card, borderRadius: 32, padding: 32, alignItems: "center",
    marginBottom: 32, borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  avatarGradient: { width: 100, height: 100, borderRadius: 50, justifyContent: "center", alignItems: "center", marginBottom: 20 },
  nameText: { color: "#fff", fontSize: 24, fontWeight: "800" },
  emailText: { color: Colors.brand.textSecondary, fontSize: 14, marginTop: 4 },
  roleBadge: { backgroundColor: "rgba(75, 57, 239, 0.15)", paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10, marginTop: 16 },
  roleText: { color: Colors.brand.primary, fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  infoSection: { marginBottom: 32 },
  sectionTitle: { color: "#fff", fontSize: 16, fontWeight: "700", marginBottom: 16, marginLeft: 4 },
  infoItem: {
    flexDirection: "row", alignItems: "center", backgroundColor: Colors.brand.card,
    padding: 16, borderRadius: 20, marginBottom: 12, borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  iconBox: { width: 44, height: 44, borderRadius: 14, backgroundColor: "rgba(75, 57, 239, 0.15)", justifyContent: "center", alignItems: "center" },
  infoTexts: { marginLeft: 16 },
  infoLabel: { color: Colors.brand.textSecondary, fontSize: 12 },
  infoValue: { color: "#fff", fontSize: 15, fontWeight: "600", marginTop: 2 },
  actionsSection: { marginTop: 8 },
  logoutBtn: { borderColor: "rgba(255, 75, 75, 0.3)", backgroundColor: "rgba(255, 75, 75, 0.05)" },
});
