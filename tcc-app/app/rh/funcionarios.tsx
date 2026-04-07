import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { buscarSetores, criarFuncionario } from "../../services/api";
import { CameraView, useCameraPermissions } from "expo-camera";

export default function RHCadastrarFuncionario() {
  const router = useRouter();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [matricula, setMatricula] = useState("");
  const [cargo, setCargo] = useState("");
  const [setores, setSetores] = useState<any[]>([]);
  const [selectedSetor, setSelectedSetor] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = React.useRef<CameraView | null>(null);

  useEffect(() => {
    const loadSetores = async () => {
      const empresaId = await SecureStore.getItemAsync("empresa_id");
      if (!empresaId) return;
      try {
        const sets = await buscarSetores(empresaId);
        setSetores(sets || []);
        if (sets?.length > 0) setSelectedSetor(sets[0].setor_id);
      } catch (e) {
        console.error(e);
      }
    };
    loadSetores();
  }, []);

  const handleCadastro = async () => {
    if (!nome || !email || !matricula) {
      Alert.alert("Erro", "Preencha nome, email e matrícula.");
      return;
    }
    if (!permission?.granted) {
      await requestPermission();
    }
    setCameraOpen(true);
  };

  const tirarFotoECadastrar = async () => {
    if (!cameraRef.current) return;
    setIsLoading(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.8 });
      const empresaId = await SecureStore.getItemAsync("empresa_id");

      await criarFuncionario(
        {
          nome,
          email,
          matricula,
          empresa_id: empresaId,
          setor_id: selectedSetor,
          cargo: cargo || null,
        },
        photo.uri
      );

      Alert.alert("Sucesso", "Funcionário cadastrado com sucesso!");
      router.back();
    } catch (error: any) {
      Alert.alert("Erro", error.message || "Falha ao cadastrar funcionário.");
    } finally {
      setIsLoading(false);
      setCameraOpen(false);
    }
  };

  if (cameraOpen) {
    return (
      <View style={{ flex: 1, backgroundColor: "#000" }}>
        <CameraView style={{ flex: 1 }} facing="front" ref={cameraRef} />
        <View style={styles.cameraOverlay}>
          <Text style={styles.cameraText}>Posicione o rosto do funcionário</Text>
        </View>
        <View style={styles.cameraControls}>
          <TouchableOpacity onPress={() => setCameraOpen(false)}>
            <Ionicons name="close" size={36} color="#fff" />
          </TouchableOpacity>
          <TouchableOpacity onPress={tirarFotoECadastrar} disabled={isLoading}>
            {isLoading ? (
              <ActivityIndicator color="#fff" size="large" />
            ) : (
              <Ionicons name="camera" size={52} color="#5B3EFF" />
            )}
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Novo Funcionário</Text>
        <View style={{ width: 22 }} />
      </View>

      <ScrollView contentContainerStyle={styles.form} showsVerticalScrollIndicator={false}>
        <Text style={styles.label}>Nome Completo</Text>
        <TextInput
          style={styles.input}
          placeholder="Ex: João da Silva"
          placeholderTextColor="#aaa"
          value={nome}
          onChangeText={setNome}
        />

        <Text style={styles.label}>E-mail</Text>
        <TextInput
          style={styles.input}
          placeholder="Ex: joao@empresa.com"
          placeholderTextColor="#aaa"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />

        <Text style={styles.label}>Matrícula</Text>
        <TextInput
          style={styles.input}
          placeholder="Ex: MAT-001"
          placeholderTextColor="#aaa"
          value={matricula}
          onChangeText={setMatricula}
        />

        <Text style={styles.label}>Cargo</Text>
        <TextInput
          style={styles.input}
          placeholder="Ex: Desenvolvedor"
          placeholderTextColor="#aaa"
          value={cargo}
          onChangeText={setCargo}
        />

        <Text style={styles.label}>Setor</Text>
        <View style={styles.setorPicker}>
          {setores.map((s) => (
            <TouchableOpacity
              key={s.setor_id}
              style={[
                styles.setorOption,
                selectedSetor === s.setor_id && styles.setorOptionSelected,
              ]}
              onPress={() => setSelectedSetor(s.setor_id)}
            >
              <Text
                style={[
                  styles.setorOptionText,
                  selectedSetor === s.setor_id && styles.setorOptionTextSelected,
                ]}
              >
                {s.nome}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity style={styles.button} onPress={handleCadastro} disabled={isLoading}>
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Cadastrar com Foto Facial</Text>
          )}
        </TouchableOpacity>

        <View style={{ height: 30 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F5F5F5" },
  header: {
    backgroundColor: "#5B3EFF",
    paddingTop: 55,
    paddingBottom: 22,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerTitle: { color: "#fff", fontSize: 18, fontWeight: "700" },
  form: { padding: 20 },
  label: { fontSize: 14, fontWeight: "600", color: "#333", marginBottom: 6, marginTop: 12 },
  input: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    fontSize: 14,
    color: "#333",
    borderWidth: 1,
    borderColor: "#e0e0e0",
  },
  setorPicker: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  setorOption: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#e0e0e0",
  },
  setorOptionSelected: { backgroundColor: "#5B3EFF", borderColor: "#5B3EFF" },
  setorOptionText: { fontSize: 13, color: "#333" },
  setorOptionTextSelected: { color: "#fff", fontWeight: "600" },
  button: {
    backgroundColor: "#5B3EFF",
    borderRadius: 14,
    padding: 16,
    alignItems: "center",
    marginTop: 24,
  },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  cameraOverlay: {
    position: "absolute",
    top: 80,
    width: "100%",
    alignItems: "center",
  },
  cameraText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  cameraControls: {
    position: "absolute",
    bottom: 50,
    width: "100%",
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
  },
});
