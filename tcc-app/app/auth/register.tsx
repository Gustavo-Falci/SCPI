import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  ActivityIndicator,
  Alert,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import { apiPost } from "../../services/api";

const { height } = Dimensions.get("window");

export default function Register() {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [tipoUsuario, setTipoUsuario] = useState("Aluno"); // 'Aluno' ou 'Professor'
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
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.topArea}>
            <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
                <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.title}>Criar Conta</Text>
          <Text style={styles.subtitle}>Junte-se ao sistema de presença inteligente</Text>

          <View style={styles.divider} />

          {/* Nome */}
          <TextInput
            placeholder="Nome Completo"
            placeholderTextColor="#BFBFBF"
            style={styles.input}
            value={nome}
            onChangeText={setNome}
          />

          {/* Email */}
          <TextInput
            placeholder="E-mail"
            placeholderTextColor="#BFBFBF"
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
          />

          {/* Seletor de Tipo */}
          <View style={styles.typeSelector}>
            <TouchableOpacity
                style={[styles.typeBtn, tipoUsuario === 'Aluno' && styles.typeBtnActive]}
                onPress={() => setTipoUsuario('Aluno')}
            >
                <Text style={[styles.typeText, tipoUsuario === 'Aluno' && styles.typeTextActive]}>Sou Aluno</Text>
            </TouchableOpacity>
            <TouchableOpacity
                style={[styles.typeBtn, tipoUsuario === 'Professor' && styles.typeBtnActive]}
                onPress={() => setTipoUsuario('Professor')}
            >
                <Text style={[styles.typeText, tipoUsuario === 'Professor' && styles.typeTextActive]}>Sou Professor</Text>
            </TouchableOpacity>
          </View>

          {/* Campo Condicional: RA ou Departamento */}
          {tipoUsuario === 'Aluno' ? (
            <TextInput
                placeholder="RA (Registro Acadêmico)"
                placeholderTextColor="#BFBFBF"
                style={styles.input}
                value={ra}
                onChangeText={setRa}
                keyboardType="numeric"
            />
          ) : (
            <TextInput
                placeholder="Departamento (Ex: Computação)"
                placeholderTextColor="#BFBFBF"
                style={styles.input}
                value={departamento}
                onChangeText={setDepartamento}
            />
          )}

          {/* Senha */}
          <View style={styles.passwordWrapper}>
            <TextInput
              placeholder="Senha"
              placeholderTextColor="#BFBFBF"
              secureTextEntry={!showPassword}
              style={styles.passwordInput}
              value={senha}
              onChangeText={setSenha}
            />
            <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
              <Ionicons
                name={showPassword ? "eye-off-outline" : "eye-outline"}
                size={18}
                color="#BFBFBF"
              />
            </TouchableOpacity>
          </View>

          {/* Confirmar Senha */}
          <View style={styles.passwordWrapper}>
            <TextInput
              placeholder="Confirmar Senha"
              placeholderTextColor="#BFBFBF"
              secureTextEntry={!showPassword}
              style={styles.passwordInput}
              value={confirmarSenha}
              onChangeText={setConfirmarSenha}
            />
          </View>

          <TouchableOpacity
            onPress={handleRegister}
            disabled={isLoading}
            style={{ width: "100%" }}
          >
            <LinearGradient
              colors={["#4B39EF", "#5E47FF"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.button}
            >
              {isLoading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Cadastrar</Text>
              )}
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.replace("/auth/login")}>
            <Text style={styles.footerText}>
              Já tem uma conta? <Text style={styles.link}>Faça Login</Text>
            </Text>
          </TouchableOpacity>

          <View style={{ height: 40 }} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0C0C12",
  },
  topArea: {
    height: 80,
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.1)",
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    flex: 1,
    backgroundColor: "#1A1A24",
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    paddingHorizontal: 30,
    paddingTop: 40,
    minHeight: height - 80,
  },
  title: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "800",
    textAlign: "center",
  },
  subtitle: {
    color: "#aaa",
    fontSize: 14,
    textAlign: 'center',
    marginTop: 8,
  },
  divider: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.1)",
    marginVertical: 25,
  },
  input: {
    backgroundColor: "rgba(255,255,255,0.05)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)",
    borderRadius: 14,
    padding: 16,
    color: "#FFFFFF",
    marginBottom: 16,
  },
  typeSelector: {
    flexDirection: 'row',
    marginBottom: 16,
    gap: 10,
  },
  typeBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.05)",
    alignItems: 'center',
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  typeBtnActive: {
    backgroundColor: "rgba(75, 57, 239, 0.2)",
    borderColor: "#4B39EF",
  },
  typeText: {
    color: "#aaa",
    fontWeight: '600',
  },
  typeTextActive: {
    color: "#fff",
  },
  passwordWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.05)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)",
    borderRadius: 14,
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  passwordInput: {
    flex: 1,
    paddingVertical: 16,
    color: "#FFFFFF",
  },
  button: {
    paddingVertical: 18,
    borderRadius: 14,
    alignItems: "center",
    marginTop: 10,
    marginBottom: 20,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  footerText: {
    color: "#D9D9D9",
    textAlign: "center",
    fontSize: 14,
  },
  link: {
    color: "#4B39EF",
    fontWeight: "700",
  },
});
