import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { storage } from "../../services/storage";

export default function Perfil() {
  const router = useRouter();

  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    const loadUser = async () => {
      const userName = await storage.getItem("user_name");
      const userEmail = await storage.getItem("user_email");

      setNome(userName || "Professor");
      setEmail(userEmail || "email@exemplo.com");
    };

    loadUser();
  }, []);

  const handleLogout = async () => {
    await storage.removeItem("access_token");
    await storage.removeItem("user_role");
    await storage.removeItem("user_id");
    await storage.removeItem("user_name");

    router.replace("/auth/login");
  };

  return (
    <View style={styles.container}>
        <LinearGradient
            colors={["#5B3EFF", "#4B2FD6"]}
            style={styles.header}
            >
            <TouchableOpacity onPress={() => router.back()}>
                <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>

            <Text style={styles.headerTitle}>Perfil</Text>

            <View style={{ width: 24 }} />
        </LinearGradient>

      {/* CARD PERFIL */}
      <View style={styles.card}>
        <Ionicons name="person-circle-outline" size={80} color="#5B3EFF" />

        <Text style={styles.name}>{nome}</Text>
        <Text style={styles.email}>{email}</Text>
      </View>

      {/* BOTÃO LOGOUT */}
      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Ionicons name="log-out-outline" size={20} color="#fff" />
        <Text style={styles.logoutText}>Sair</Text>
      </TouchableOpacity>

        <View style={styles.bottomMenu}>
            <TouchableOpacity onPress={() => router.replace("/professor/home")}>
                <Ionicons name="home-outline" size={22} color="#aaa" />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => router.push("/professor/turmas")}>
                <Ionicons name="clipboard-outline" size={22} color="#aaa" />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => router.push("/professor/horarios-turmas")}>
                <Ionicons name="calendar-outline" size={22} color="#aaa" />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => router.push("/professor/perfil")}>
                <Ionicons name="person-outline" size={22} color="#7C4DFF" />
            </TouchableOpacity>
        </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F2F2F2",
  },

  header: {
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
    fontSize: 20,
    fontWeight: "700",
  },

  card: {
    marginTop: 40,
    marginHorizontal: 20,
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 25,
    alignItems: "center",
    elevation: 3,
  },

  name: {
    marginTop: 15,
    fontSize: 18,
    fontWeight: "700",
  },

  email: {
    marginTop: 5,
    fontSize: 14,
    color: "#777",
  },

  logoutButton: {
    marginTop: 40,
    marginHorizontal: 20,
    backgroundColor: "#FF3B30",
    padding: 15,
    borderRadius: 12,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },

  logoutText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
    marginLeft: 8,
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