import { useState, useRef, useEffect } from "react";
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
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { CameraView, useCameraPermissions } from "expo-camera";

import { apiPost, apiPostFormData } from "../../services/api";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Colors } from "../../constants/theme";

const { width, height } = Dimensions.get("window");

export default function Register() {
  // Etapas: 'dados' ou 'face'
  const [step, setStep] = useState<'dados' | 'face'>('dados');
  
  // Dados do form
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [tipoUsuario, setTipoUsuario] = useState<"Aluno" | "Professor">("Aluno");
  const [ra, setRa] = useState("");
  const [departamento, setDepartamento] = useState("");

  // Estado da câmera
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView | null>(null);
  const [createdUserId, setCreatedUserId] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleRegisterData = async () => {
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

      const resp = await apiPost("/auth/register", payload);
      
      if (tipoUsuario === "Aluno") {
          // Se for aluno, vamos para a etapa da face
          // Precisamos que o backend retorne o usuario_id no registro.
          // Vou assumir que ele retorna ou buscar pelo email se necessário.
          // Por enquanto, vamos simular que ele retornou o ID.
          setStep('face');
      } else {
          Alert.alert("Sucesso", "Conta de professor criada com sucesso!");
          router.replace("/auth/login");
      }
    } catch (error: any) {
      Alert.alert("Falha no Registro", error.message || "Erro ao criar conta.");
    } finally {
      setIsLoading(false);
    }
  };

  const tirarFotoERegistrar = async () => {
    if (!cameraRef.current || isLoading) return;

    setIsLoading(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.7 });
      
      const formData = new FormData();
      // Como acabamos de criar, vamos usar o email para o backend localizar o aluno
      formData.append("user_id", ""); // O backend vai precisar localizar por email se o ID não vier
      formData.append("nome", nome);
      formData.append("email", email);
      formData.append("ra", ra);

      const localUri = photo.uri;
      const filename = localUri.split('/').pop() || 'face.jpg';
      const type = `image/jpeg`;

      formData.append("foto", { uri: localUri, name: filename, type: type } as any);

      await apiPostFormData("/alunos/cadastrar-face", formData);
      
      Alert.alert("Sucesso!", "Cadastro completo com biometria facial!", [
        { text: "Ir para Login", onPress: () => router.replace("/auth/login") }
      ]);
    } catch (error: any) {
      Alert.alert("Erro na Biometria", "Não foi possível processar sua face. Você poderá tentar novamente após o login.");
      router.replace("/auth/login");
    } finally {
      setIsLoading(false);
    }
  };

  if (step === 'face') {
    return (
      <View style={styles.container}>
        <CameraView style={StyleSheet.absoluteFill} facing="front" ref={cameraRef} />
        <View style={styles.overlay}>
           <View style={styles.scannerHeader}>
              <Text style={styles.scannerTitle}>Último Passo: Biometria</Text>
              <Text style={styles.scannerSub}>Posicione seu rosto na moldura</Text>
           </View>
           <View style={styles.faceFrameContainer}>
              <View style={styles.faceFrame} />
           </View>
           <View style={styles.scannerFooter}>
              <TouchableOpacity style={styles.captureBtn} onPress={tirarFotoERegistrar} disabled={isLoading}>
                 {isLoading ? <ActivityIndicator color="#fff" /> : <View style={styles.captureBtnInner} />}
              </TouchableOpacity>
              <TouchableOpacity onPress={() => router.replace("/auth/login")} style={{ marginTop: 20 }}>
                 <Text style={{ color: '#fff', opacity: 0.7 }}>Pular por enquanto</Text>
              </TouchableOpacity>
           </View>
        </View>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={{ flex: 1 }}>
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ flexGrow: 1 }}>
          <View style={styles.header}>
            <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
              <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>
          </View>

          <View style={styles.card}>
            <Text style={styles.title}>Criar Conta</Text>
            <Text style={styles.subtitle}>Preencha seus dados para começar</Text>

            <View style={styles.divider} />

            <Input label="Nome Completo" placeholder="Ex: João Silva" value={nome} onChangeText={setNome} icon="person-outline" />
            <Input label="E-mail" placeholder="seu@email.com" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" icon="mail-outline" />

            <Text style={styles.sectionLabel}>Eu sou:</Text>
            <View style={styles.typeSelector}>
              <TouchableOpacity style={[styles.typeBtn, tipoUsuario === "Aluno" && styles.typeBtnActive]} onPress={() => setTipoUsuario("Aluno")}>
                <Ionicons name="school-outline" size={20} color={tipoUsuario === "Aluno" ? "#fff" : "#aaa"} />
                <Text style={[styles.typeText, tipoUsuario === "Aluno" && styles.typeTextActive]}>Aluno</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.typeBtn, tipoUsuario === "Professor" && styles.typeBtnActive]} onPress={() => setTipoUsuario("Professor")}>
                <Ionicons name="briefcase-outline" size={20} color={tipoUsuario === "Professor" ? "#fff" : "#aaa"} />
                <Text style={[styles.typeText, tipoUsuario === "Professor" && styles.typeTextActive]}>Professor</Text>
              </TouchableOpacity>
            </View>

            {tipoUsuario === "Aluno" ? (
              <Input label="RA" placeholder="000000" value={ra} onChangeText={setRa} keyboardType="numeric" icon="id-card-outline" />
            ) : (
              <Input label="Departamento" placeholder="Ex: Engenharia" value={departamento} onChangeText={setDepartamento} icon="business-outline" />
            )}

            <Input label="Senha" placeholder="••••••" value={senha} onChangeText={setSenha} secureTextEntry={!showPassword} icon="lock-closed-outline" />
            <Input label="Confirmar Senha" placeholder="••••••" value={confirmarSenha} onChangeText={setSenha} secureTextEntry={!showPassword} icon="checkmark-circle-outline" />

            <Button title={tipoUsuario === "Aluno" ? "PRÓXIMO: CADASTRAR FACE" : "CADASTRAR"} onPress={handleRegisterData} loading={isLoading} style={{ marginTop: 10 }} />

            <TouchableOpacity onPress={() => router.replace("/auth/login")} style={styles.footer}>
              <Text style={styles.footerText}>Já tem uma conta? <Text style={styles.link}>Faça Login</Text></Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  header: { height: 60, justifyContent: "center", paddingHorizontal: 20, marginTop: 10 },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: "rgba(255,255,255,0.1)", justifyContent: "center", alignItems: "center" },
  card: { flex: 1, backgroundColor: Colors.brand.card, borderTopLeftRadius: 40, borderTopRightRadius: 40, paddingHorizontal: 24, paddingTop: 40, minHeight: height - 70 },
  title: { color: Colors.brand.text, fontSize: 28, fontWeight: "800", textAlign: "center" },
  subtitle: { color: Colors.brand.textSecondary, fontSize: 14, textAlign: "center", marginTop: 8 },
  divider: { height: 1, backgroundColor: "rgba(255,255,255,0.1)", marginVertical: 24 },
  sectionLabel: { color: Colors.brand.text, fontSize: 14, fontWeight: "600", marginBottom: 12, marginLeft: 4 },
  typeSelector: { flexDirection: "row", marginBottom: 20, gap: 12 },
  typeBtn: { flex: 1, flexDirection: "row", paddingVertical: 14, borderRadius: 14, backgroundColor: "rgba(255,255,255,0.05)", alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)", gap: 8 },
  typeBtnActive: { backgroundColor: "rgba(75, 57, 239, 0.15)", borderColor: Colors.brand.primary },
  typeText: { color: Colors.brand.textSecondary, fontWeight: "600", fontSize: 15 },
  typeTextActive: { color: Colors.brand.text },
  footer: { marginTop: 20, alignItems: "center" },
  footerText: { color: Colors.brand.textSecondary, fontSize: 14 },
  link: { color: Colors.brand.primary, fontWeight: "700" },
  // Scanner styles
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 60 },
  scannerHeader: { alignItems: 'center' },
  scannerTitle: { color: '#fff', fontSize: 22, fontWeight: '800' },
  scannerSub: { color: 'rgba(255,255,255,0.7)', marginTop: 8 },
  faceFrameContainer: { width: 280, height: 380, borderRadius: 140, borderWidth: 2, borderColor: Colors.brand.primary, overflow: 'hidden' },
  faceFrame: { flex: 1 },
  scannerFooter: { alignItems: 'center', width: '100%' },
  captureBtn: { width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center', alignItems: 'center' },
  captureBtnInner: { width: 64, height: 64, borderRadius: 32, backgroundColor: '#fff' }
});
