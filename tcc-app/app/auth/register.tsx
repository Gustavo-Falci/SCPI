import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Dimensions,
  Alert,
  ScrollView,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { apiPost } from "../../services/api";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Colors } from "../../constants/theme";

const { height } = Dimensions.get("window");

export default function Register() {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [tipoUsuario, setTipoUsuario] = useState<"Aluno" | "Professor">("Aluno");
  const [ra, setRa] = useState("");
  const [departamento, setDepartamento] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleRegister = async () => {
    if (!nome || !email || !senha || !confirmarSenha) {
      Alert.alert("Erro", "Por favor, preencha todos os campos obrigatórios.");
      return;
    }

    if (senha !== confirmarSenha) {
      Alert.alert("Erro", "As senhas não coincidem.");
      return;
    }

    if (tipoUsuario === "Aluno" && !ra) {
      Alert.alert("Erro", "O RA é obrigatório para alunos.");
      return;
    }

    setIsLoading(true);
    try {
      const payload = {
        nome,
        email,
        senha,
        tipo_usuario: tipoUsuario,
        ra: tipoUsuario === "Aluno" ? ra : null,
        departamento: tipoUsuario === "Professor" ? departamento : null,
      };

      await apiPost("/auth/register", payload);

      Alert.alert("Sucesso", "Conta criada com sucesso! Faça login para continuar.", [
        { text: "OK", onPress: () => router.replace("/auth/login") }
      ]);
    } catch (error: any) {
      Alert.alert("Falha no Registro", error.message || "Erro ao criar conta.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
      >
        <ScrollView 
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ flexGrow: 1 }}
        >
          <View style={styles.header}>
            <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
              <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>
          </View>

          <View style={styles.card}>
            <Text style={styles.title}>Criar Conta</Text>
            <Text style={styles.subtitle}>Junte-se ao sistema de presença inteligente</Text>

            <View style={styles.divider} />

            <Input
              label="Nome Completo"
              placeholder="Ex: João Silva"
              value={nome}
              onChangeText={setNome}
              icon="person-outline"
            />

            <Input
              label="E-mail"
              placeholder="seu@email.com"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              icon="mail-outline"
            />

            <Text style={styles.sectionLabel}>Eu sou:</Text>
            <View style={styles.typeSelector}>
              <TouchableOpacity
                style={[styles.typeBtn, tipoUsuario === "Aluno" && styles.typeBtnActive]}
                onPress={() => setTipoUsuario("Aluno")}
              >
                <Ionicons 
                  name="school-outline" 
                  size={20} 
                  color={tipoUsuario === "Aluno" ? "#fff" : "#aaa"} 
                />
                <Text style={[styles.typeText, tipoUsuario === "Aluno" && styles.typeTextActive]}>Aluno</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={[styles.typeBtn, tipoUsuario === "Professor" && styles.typeBtnActive]}
                onPress={() => setTipoUsuario("Professor")}
              >
                <Ionicons 
                  name="briefcase-outline" 
                  size={20} 
                  color={tipoUsuario === "Professor" ? "#fff" : "#aaa"} 
                />
                <Text style={[styles.typeText, tipoUsuario === "Professor" && styles.typeTextActive]}>Professor</Text>
              </TouchableOpacity>
            </View>

            {tipoUsuario === "Aluno" ? (
              <Input
                label="RA (Registro Acadêmico)"
                placeholder="000000"
                value={ra}
                onChangeText={setRa}
                keyboardType="numeric"
                icon="id-card-outline"
              />
            ) : (
              <Input
                label="Departamento"
                placeholder="Ex: Engenharia"
                value={departamento}
                onChangeText={setDepartamento}
                icon="business-outline"
              />
            )}

            <Input
              label="Senha"
              placeholder="Mínimo 6 caracteres"
              value={senha}
              onChangeText={setSenha}
              secureTextEntry={!showPassword}
              icon="lock-closed-outline"
              rightIcon={showPassword ? "eye-off-outline" : "eye-outline"}
              onRightIconPress={() => setShowPassword(!showPassword)}
            />

            <Input
              label="Confirmar Senha"
              placeholder="Repita sua senha"
              value={confirmarSenha}
              onChangeText={setConfirmarSenha}
              secureTextEntry={!showPassword}
              icon="checkmark-circle-outline"
            />

            <Button
              title="Cadastrar"
              onPress={handleRegister}
              loading={isLoading}
              style={{ marginTop: 10 }}
            />

            <TouchableOpacity 
              onPress={() => router.replace("/auth/login")}
              style={styles.footer}
            >
              <Text style={styles.footerText}>
                Já tem uma conta? <Text style={styles.link}>Faça Login</Text>
              </Text>
            </TouchableOpacity>

            <View style={{ height: 40 }} />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.brand.background,
  },
  header: {
    height: 60,
    justifyContent: "center",
    paddingHorizontal: 20,
    marginTop: 10,
  },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "rgba(255,255,255,0.1)",
    justifyContent: "center",
    alignItems: "center",
  },
  card: {
    flex: 1,
    backgroundColor: Colors.brand.card,
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    paddingHorizontal: 24,
    paddingTop: 40,
    minHeight: height - 70,
  },
  title: {
    color: Colors.brand.text,
    fontSize: 28,
    fontWeight: "800",
    textAlign: "center",
  },
  subtitle: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginTop: 8,
  },
  divider: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.1)",
    marginVertical: 24,
  },
  sectionLabel: {
    color: Colors.brand.text,
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 12,
    marginLeft: 4,
  },
  typeSelector: {
    flexDirection: "row",
    marginBottom: 20,
    gap: 12,
  },
  typeBtn: {
    flex: 1,
    flexDirection: "row",
    paddingVertical: 14,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.05)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    gap: 8,
  },
  typeBtnActive: {
    backgroundColor: "rgba(75, 57, 239, 0.15)",
    borderColor: Colors.brand.primary,
  },
  typeText: {
    color: Colors.brand.textSecondary,
    fontWeight: "600",
    fontSize: 15,
  },
  typeTextActive: {
    color: Colors.brand.text,
  },
  footer: {
    marginTop: 20,
    alignItems: "center",
  },
  footerText: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
  },
  link: {
    color: Colors.brand.primary,
    fontWeight: "700",
  },
});
