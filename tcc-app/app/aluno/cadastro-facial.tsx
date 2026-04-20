import { Feather, Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useRef, useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Alert,
  ActivityIndicator,
  StatusBar,
  Dimensions,
  ScrollView,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { storage } from "../../services/storage";
import { apiPostFormData } from "../../services/api";
import { Colors } from "../../constants/theme";

const { width, height } = Dimensions.get("window");

export default function CadastroFacial() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraOpen, setCameraOpen] = useState(false);
  const cameraRef = useRef<CameraView | null>(null);
  const [loading, setLoading] = useState(false);
  const [userData, setUserData] = useState<any>(null);
  const [consentimento, setConsentimento] = useState(false);

  useEffect(() => {
    const loadUser = async () => {
      const nome = await storage.getItem("user_name");
      const email = await storage.getItem("user_email");
      const ra = await storage.getItem("user_ra");
      const id = await storage.getItem("user_id");
      setUserData({ nome, email, ra, id });
    };
    loadUser();
  }, []);

  const tirarFoto = async () => {
    if (!cameraRef.current || loading) return;

    if (!userData?.email || !userData?.ra) {
        Alert.alert("Erro de Dados", "Seus dados (Email/RA) não foram localizados. Por favor, faça logout e entre novamente.");
        return;
    }

    setLoading(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.7,
        base64: false,
      });
      
      const formData = new FormData();
      formData.append("user_id", userData?.id || "");
      formData.append("nome", userData?.nome || "Aluno");
      formData.append("email", userData?.email || "");
      formData.append("ra", userData?.ra || "");

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

      await apiPostFormData("/alunos/cadastrar-face", formData);
      
      Alert.alert("Sucesso!", "Sua biometria facial foi atualizada com sucesso!");
      router.back();
    } catch (error: any) {
      console.error("Erro no cadastro facial:", error);
      Alert.alert("Erro", error.message || "Não foi possível processar sua face. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

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
          
          {/* BOTÃO FECHAR (TOPO ESQUERDO) */}
          <TouchableOpacity 
            style={[styles.closeBtnTop, { top: insets.top + 20 }]} 
            onPress={() => setCameraOpen(false)}
            disabled={loading}
          >
            <Ionicons name="close" size={30} color="#fff" />
          </TouchableOpacity>

          <View style={styles.scannerContainer}>
            <Text style={styles.cameraHint}>
               Posicione seu rosto dentro da moldura
            </Text>

            {/* MOLDURA OVAL COM A CÂMERA DENTRO */}
            <View style={styles.faceFrameContainer}>
              <View style={styles.ovalMask}>
                <CameraView
                  style={styles.cameraPreview}
                  facing="front"
                  ref={cameraRef}
                />
              </View>
              {/* Borda decorativa azul */}
              <View style={styles.faceFrameBorder} />
            </View>
          </View>

          {/* BOTÕES DE CAPTURA (BASE) */}
          <View style={styles.cameraControls}>
            <TouchableOpacity 
              style={styles.captureBtn} 
              onPress={tirarFoto}
              disabled={loading}
            >
              <View style={styles.captureBtnInner} />
            </TouchableOpacity>
          </View>

          {loading && (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color={Colors.brand.primary} />
              <Text style={styles.loadingText}>Processando Biometria...</Text>
            </View>
          )}
        </View>
      ) : (
        <SafeAreaView style={{ flex: 1 }}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
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
              <Text style={styles.heroTitle}>Atualizar Scanner</Text>
              <Text style={styles.heroSubtitle}>Sua face será re-indexada na AWS para garantir maior precisão.</Text>
            </View>

            <Text style={styles.sectionLabel}>Antes de começar</Text>
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

            <Text style={styles.sectionLabel}>Privacidade</Text>
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
              <Text style={styles.mainButtonText}>Atualizar Face</Text>
            </TouchableOpacity>
            {!consentimento && (
              <Text style={styles.hintText}>Marque o consentimento acima para continuar</Text>
            )}
          </ScrollView>
        </SafeAreaView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, height: 60 },
  headerTitle: { fontSize: 18, fontWeight: "800", color: "#fff" },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.brand.card, justifyContent: "center", alignItems: "center" },
  scrollContent: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 40 },
  heroSection: { alignItems: "center", marginBottom: 28, marginTop: 8 },
  heroIconBadge: { width: 96, height: 96, borderRadius: 48, backgroundColor: "rgba(75, 57, 239, 0.12)", justifyContent: "center", alignItems: "center", marginBottom: 16, borderWidth: 1, borderColor: "rgba(75, 57, 239, 0.25)" },
  heroTitle: { color: "#fff", fontSize: 24, fontWeight: "800", textAlign: "center" },
  heroSubtitle: { color: Colors.brand.textSecondary, fontSize: 14, textAlign: "center", marginTop: 6, paddingHorizontal: 16, lineHeight: 20 },
  sectionLabel: { color: Colors.brand.textSecondary, fontSize: 11, fontWeight: "700", letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 12, marginLeft: 4 },
  instructionsContainer: { gap: 10, marginBottom: 24 },
  instructionItem: { flexDirection: "row", alignItems: "center", gap: 14, backgroundColor: "rgba(255,255,255,0.03)", paddingHorizontal: 14, paddingVertical: 12, borderRadius: 14 },
  iconCircle: { width: 36, height: 36, borderRadius: 18, backgroundColor: "rgba(75, 57, 239, 0.12)", justifyContent: "center", alignItems: "center" },
  instructionText: { flex: 1, color: Colors.brand.text, fontSize: 14, fontWeight: "500" },
  mainButton: { backgroundColor: Colors.brand.primary, height: 56, borderRadius: 16, flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 8, shadowColor: Colors.brand.primary, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6 },
  mainButtonDisabled: { opacity: 0.35, shadowOpacity: 0 },
  mainButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  hintText: { color: Colors.brand.textSecondary, fontSize: 12, textAlign: "center", marginTop: 12, fontStyle: "italic" },
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
  buttonText: { color: "#fff", fontWeight: "700" }
});
