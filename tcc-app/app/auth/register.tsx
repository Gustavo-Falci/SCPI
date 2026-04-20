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
  StatusBar,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
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
  const [cameraOpen, setCameraOpen] = useState(false);

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [consentimento, setConsentimento] = useState(false);
  const router = useRouter();
  const insets = useSafeAreaInsets();

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

    // Aluno: ainda NÃO gravamos no banco — só avança para a etapa da face.
    // A conta só será criada após a face ser indexada com sucesso.
    if (tipoUsuario === "Aluno") {
      setStep('face');
      return;
    }

    // Professor: cadastro imediato (não precisa de face).
    setIsLoading(true);
    try {
      const payload = {
        nome,
        email,
        senha,
        tipo_usuario: tipoUsuario,
        ra: null,
        departamento,
      };
      await apiPost("/auth/register", payload);
      Alert.alert("Sucesso", "Conta de professor criada com sucesso!");
      router.replace("/auth/login");
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
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.7,
        base64: false,
      });

      const formData = new FormData();
      formData.append("nome", nome);
      formData.append("email", email);
      formData.append("senha", senha);
      formData.append("ra", ra);

      const localUri = photo.uri;
      const filename = localUri.split('/').pop() || 'face.jpg';
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : `image/jpeg`;

      formData.append("foto", {
        uri: localUri,
        name: filename,
        type: type,
      } as any);
      formData.append("consentimento_biometrico", "true");

      await apiPostFormData("/auth/register-aluno-com-face", formData);

      Alert.alert("Sucesso!", "Conta criada com biometria facial!", [
        { text: "Ir para Login", onPress: () => router.replace("/auth/login") }
      ]);
    } catch (error: any) {
      const msg = error?.message || "Erro desconhecido.";
      console.log("[register-aluno-com-face] erro:", msg);
      // Nenhum dado foi gravado no banco — usuário pode tentar novamente na mesma tela.
      Alert.alert("Erro no Cadastro", `${msg}\n\nNada foi salvo. Tente novamente.`);
      setCameraOpen(false);
    } finally {
      setIsLoading(false);
    }
  };

  if (step === 'face') {
    if (!permission) return <View style={styles.container} />;

    if (!permission.granted) {
      return (
        <SafeAreaView style={styles.container}>
          <View style={styles.center}>
            <Ionicons name="camera-outline" size={80} color={Colors.brand.textSecondary} />
            <Text style={styles.permissionText}>Precisamos de acesso à sua câmera para realizar o cadastro facial.</Text>
            <TouchableOpacity style={styles.primaryButton} onPress={requestPermission}>
              <Text style={styles.buttonText}>Permitir Câmera</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      );
    }

    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" />

        {cameraOpen ? (
          <View style={styles.cameraWrapper}>
            <TouchableOpacity
              style={[styles.closeBtnTop, { top: insets.top + 20 }]}
              onPress={() => setCameraOpen(false)}
              disabled={isLoading}
            >
              <Ionicons name="close" size={30} color="#fff" />
            </TouchableOpacity>

            <View style={styles.scannerContainer}>
              <Text style={styles.cameraHint}>
                Posicione seu rosto dentro da moldura
              </Text>

              <View style={styles.faceFrameContainer}>
                <View style={styles.ovalMask}>
                  <CameraView
                    style={styles.cameraPreview}
                    facing="front"
                    ref={cameraRef}
                  />
                </View>
                <View style={styles.faceFrameBorder} />
              </View>
            </View>

            <View style={styles.cameraControls}>
              <TouchableOpacity
                style={styles.captureBtn}
                onPress={tirarFotoERegistrar}
                disabled={isLoading}
              >
                <View style={styles.captureBtnInner} />
              </TouchableOpacity>
            </View>

            {isLoading && (
              <View style={styles.loadingOverlay}>
                <ActivityIndicator size="large" color={Colors.brand.primary} />
                <Text style={styles.loadingText}>Processando Biometria...</Text>
              </View>
            )}
          </View>
        ) : (
          <SafeAreaView style={{ flex: 1 }}>
            <View style={styles.faceHeader}>
              <TouchableOpacity onPress={() => router.replace("/auth/login")} style={styles.faceBackBtn}>
                <Ionicons name="arrow-back" size={24} color="#fff" />
              </TouchableOpacity>
              <Text style={styles.headerTitle}>Biometria Facial</Text>
              <View style={{ width: 44 }} />
            </View>

            <ScrollView
              style={{ flex: 1 }}
              contentContainerStyle={styles.scrollContent}
              showsVerticalScrollIndicator={false}
            >
              <View style={styles.heroSection}>
                <View style={styles.heroIconBadge}>
                  <MaterialCommunityIcons name="face-recognition" size={52} color={Colors.brand.primary} />
                </View>
                <Text style={styles.heroTitle}>Último Passo</Text>
                <Text style={styles.heroSubtitle}>Sua face será indexada na AWS para garantir maior precisão no reconhecimento.</Text>
              </View>

              <Text style={styles.faceSectionLabel}>Antes de começar</Text>
              <View style={styles.instructionsContainer}>
                <View style={styles.instructionItem}>
                  <View style={styles.iconCircle}>
                    <Ionicons name="sunny-outline" size={18} color={Colors.brand.primary} />
                  </View>
                  <Text style={styles.instructionText}>Procure um ambiente bem iluminado</Text>
                </View>

                <View style={styles.instructionItem}>
                  <View style={styles.iconCircle}>
                    <Ionicons name="glasses-outline" size={18} color={Colors.brand.primary} />
                  </View>
                  <Text style={styles.instructionText}>Remova óculos escuros e máscara</Text>
                </View>

                <View style={styles.instructionItem}>
                  <View style={styles.iconCircle}>
                    <Ionicons name="person-outline" size={18} color={Colors.brand.primary} />
                  </View>
                  <Text style={styles.instructionText}>Mantenha uma expressão neutra</Text>
                </View>
              </View>

              <Text style={styles.faceSectionLabel}>Privacidade</Text>
              <View style={[styles.consentCard, consentimento && styles.consentCardActive]}>
                <View style={styles.consentHeader}>
                  <Ionicons name="shield-checkmark-outline" size={22} color={Colors.brand.primary} />
                  <Text style={styles.consentTitle}>Consentimento LGPD</Text>
                </View>
                <Text style={styles.consentBody}>
                  Autorizo o SCPI a coletar e processar minha imagem facial para <Text style={styles.consentBodyStrong}>controle de presença nas aulas</Text>. Os dados são armazenados de forma segura (AWS Rekognition + S3) e posso revogar este consentimento a qualquer momento pelo meu perfil. (LGPD art. 11)
                </Text>
                <TouchableOpacity
                  style={styles.consentRow}
                  onPress={() => setConsentimento((v) => !v)}
                  activeOpacity={0.8}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <View style={[styles.checkbox, consentimento && styles.checkboxActive]}>
                    {consentimento && <Ionicons name="checkmark" size={16} color="#fff" />}
                  </View>
                  <Text style={styles.consentCheckLabel}>Li e concordo com o tratamento dos meus dados biométricos.</Text>
                </TouchableOpacity>
              </View>

              <TouchableOpacity
                style={[styles.mainButton, !consentimento && styles.mainButtonDisabled]}
                onPress={() => consentimento && setCameraOpen(true)}
                disabled={!consentimento}
                activeOpacity={0.85}
              >
                <Ionicons name="camera" size={22} color="#fff" />
                <Text style={styles.mainButtonText}>Cadastrar Face</Text>
              </TouchableOpacity>
              {!consentimento && (
                <Text style={styles.hintText}>Marque o consentimento acima para continuar</Text>
              )}

              <TouchableOpacity onPress={() => router.replace("/auth/login")} style={styles.skipLink}>
                <Text style={styles.skipLinkText}>Pular por enquanto</Text>
              </TouchableOpacity>
            </ScrollView>
          </SafeAreaView>
        )}
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
            <Input label="Confirmar Senha" placeholder="••••••" value={confirmarSenha} onChangeText={setConfirmarSenha} secureTextEntry={!showPassword} icon="checkmark-circle-outline" />

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

  // Tela de Biometria Facial (espelhada de cadastro-facial.tsx)
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40 },
  faceHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, height: 60 },
  headerTitle: { fontSize: 18, fontWeight: "800", color: "#fff" },
  faceBackBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.brand.card, justifyContent: "center", alignItems: "center" },
  scrollContent: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 40 },
  heroSection: { alignItems: "center", marginBottom: 28, marginTop: 8 },
  heroIconBadge: { width: 96, height: 96, borderRadius: 48, backgroundColor: "rgba(75, 57, 239, 0.12)", justifyContent: "center", alignItems: "center", marginBottom: 16, borderWidth: 1, borderColor: "rgba(75, 57, 239, 0.25)" },
  heroTitle: { color: "#fff", fontSize: 24, fontWeight: "800", textAlign: "center" },
  heroSubtitle: { color: Colors.brand.textSecondary, fontSize: 14, textAlign: "center", marginTop: 6, paddingHorizontal: 16, lineHeight: 20 },
  faceSectionLabel: { color: Colors.brand.textSecondary, fontSize: 11, fontWeight: "700", letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 12, marginLeft: 4 },
  instructionsContainer: { gap: 10, marginBottom: 24 },
  instructionItem: { flexDirection: "row", alignItems: "center", gap: 14, backgroundColor: "rgba(255,255,255,0.03)", paddingHorizontal: 14, paddingVertical: 12, borderRadius: 14 },
  iconCircle: { width: 36, height: 36, borderRadius: 18, backgroundColor: "rgba(75, 57, 239, 0.12)", justifyContent: "center", alignItems: "center" },
  instructionText: { flex: 1, color: Colors.brand.text, fontSize: 14, fontWeight: "500" },
  mainButton: { backgroundColor: Colors.brand.primary, height: 56, borderRadius: 16, flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 8, shadowColor: Colors.brand.primary, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6 },
  mainButtonDisabled: { opacity: 0.35, shadowOpacity: 0 },
  mainButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  hintText: { color: Colors.brand.textSecondary, fontSize: 12, textAlign: "center", marginTop: 12, fontStyle: "italic" },
  skipLink: { marginTop: 20, alignItems: "center", paddingVertical: 8 },
  skipLinkText: { color: "#fff", opacity: 0.6, fontSize: 14, fontWeight: "500" },
  consentCard: { backgroundColor: Colors.brand.card, borderRadius: 18, padding: 18, marginBottom: 24, borderWidth: 1, borderColor: "rgba(255,255,255,0.08)" },
  consentCardActive: { borderColor: Colors.brand.primary, backgroundColor: "rgba(75, 57, 239, 0.06)" },
  consentHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  consentTitle: { color: "#fff", fontSize: 15, fontWeight: "700" },
  consentBody: { color: Colors.brand.textSecondary, fontSize: 13, lineHeight: 20, marginBottom: 16 },
  consentBodyStrong: { color: Colors.brand.text, fontWeight: "700" },
  consentRow: { flexDirection: "row", alignItems: "flex-start", gap: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.06)" },
  checkbox: { width: 22, height: 22, borderRadius: 6, borderWidth: 2, borderColor: Colors.brand.textSecondary, justifyContent: "center", alignItems: "center", marginTop: 1 },
  checkboxActive: { backgroundColor: Colors.brand.primary, borderColor: Colors.brand.primary },
  consentCheckLabel: { flex: 1, color: Colors.brand.text, fontSize: 13, fontWeight: "500", lineHeight: 18 },
  cameraWrapper: { flex: 1, backgroundColor: "#000" },
  scannerContainer: { flex: 1, justifyContent: "center", alignItems: "center" },
  faceFrameContainer: { width: 280, height: 420, justifyContent: "center", alignItems: "center" },
  ovalMask: { width: 280, height: 420, borderRadius: 140, overflow: "hidden", backgroundColor: "#000" },
  cameraPreview: { flex: 1, width: "100%" },
  faceFrameBorder: { position: "absolute", width: 280, height: 420, borderRadius: 140, borderWidth: 3, borderColor: Colors.brand.primary },
  cameraControls: { position: "absolute", bottom: 50, width: "100%", flexDirection: "row", justifyContent: "center", alignItems: "center" },
  captureBtn: { width: 80, height: 80, borderRadius: 40, backgroundColor: "rgba(255,255,255,0.3)", justifyContent: "center", alignItems: "center" },
  captureBtnInner: { width: 64, height: 64, borderRadius: 32, backgroundColor: "#fff" },
  closeBtnTop: { position: "absolute", left: 25, width: 50, height: 50, borderRadius: 25, backgroundColor: "rgba(255,255,255,0.1)", justifyContent: "center", alignItems: "center", zIndex: 20 },
  cameraHint: { color: "#fff", fontSize: 18, fontWeight: "700", textAlign: "center", paddingHorizontal: 40, marginBottom: 30 },
  loadingOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0,0,0,0.8)", justifyContent: "center", alignItems: "center", zIndex: 30 },
  loadingText: { color: "#fff", marginTop: 20, fontSize: 16, fontWeight: "700" },
  permissionText: { color: Colors.brand.textSecondary, textAlign: "center", marginVertical: 20, fontSize: 16 },
  primaryButton: { backgroundColor: Colors.brand.primary, paddingHorizontal: 30, paddingVertical: 15, borderRadius: 12 },
  buttonText: { color: "#fff", fontWeight: "700" },
});
