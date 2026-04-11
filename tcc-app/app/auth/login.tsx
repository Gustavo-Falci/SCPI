import { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Dimensions,
  ActivityIndicator,
  Alert
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import { storage } from "../../services/storage";
import { loginRequest } from "../../services/api";

const { height } = Dimensions.get("window");

export default function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // Verifica se o usuário já está logado e redireciona se necessário
    const checkTokenAndRedirect = async () => {
      const token = await storage.getItem("access_token");
      if (token) {
        const role = await storage.getItem("user_role");
        if (role === "Admin") router.replace("/admin/home");
        else if (role === "RH") router.replace("/rh/home");
        else router.replace("/funcionario/home");
      }
    };
    checkTokenAndRedirect();
  }, []);


  const handleLogin = async () => {
    if (!email || !senha) {
      Alert.alert("Erro", "Por favor, preencha todos os campos.");
      return;
    }

    setIsLoading(true);
    try {
      const resp = await loginRequest(email, senha);

      // Token will be saved here later
      await SecureStore.setItemAsync("access_token", resp.access_token);
      await SecureStore.setItemAsync("user_role", resp.user_role);

      // Redirect based on role
      if (resp.user_role === "Professor") {
        router.replace("/professor/home");
      } else {
        router.replace("/aluno/home");
      }

    } catch (error: any) {
      Alert.alert("Falha no Login", error.message || "E-mail ou senha incorretos.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Parte escura superior */}
      <View style={styles.topArea} />

      {/* Card */}
      <View style={styles.card}>
        <Text style={styles.title}>Bem-vindo!</Text>

        <View style={styles.divider} />

        <TextInput
          placeholder="Email"
          placeholderTextColor="#BFBFBF"
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
        />

        <View style={styles.passwordWrapper}>
          <TextInput
            placeholder="Password"
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

        <TouchableOpacity onPress={handleLogin} disabled={isLoading} style={{ width: '100%' }}>
          <LinearGradient
            colors={["#4B39EF", "#5E47FF"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.button}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Sign In</Text>
            )}
          </LinearGradient>
        </TouchableOpacity>

        <Text style={styles.forgotText}>
          Esqueceu sua senha?{" "}
          <Text style={styles.link}>Clique aqui</Text>
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0C0C12",
  },

  topArea: {
    height: height * 0.25,
    backgroundColor: "#0C0C12",
  },

  card: {
    flex: 1,
    backgroundColor: "#3A262F",
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    paddingHorizontal: 30,
    paddingTop: 45,
  },

  title: {
    color: "#FFFFFF",
    fontSize: 32,
    fontWeight: "800",
    textAlign: "center",
  },

  divider: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.35)",
    marginVertical: 25,
  },

  input: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.25)",
    borderRadius: 14,
    padding: 16,
    color: "#FFFFFF",
    marginBottom: 20,
  },

  passwordWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.25)",
    borderRadius: 14,
    paddingHorizontal: 16,
    marginBottom: 30,
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
    marginBottom: 25,
  },

  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },

  forgotText: {
    color: "#D9D9D9",
    textAlign: "center",
    fontSize: 13,
  },

  link: {
    color: "#4B39EF",
    fontWeight: "700",
  },
});