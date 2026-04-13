import { Feather, Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useRef, useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { apiPostFormData } from "../../services/api";
import { Alert, ActivityIndicator } from "react-native";

export default function CadastroFacial() {

  const router = useRouter();

  const [permission, requestPermission] = useCameraPermissions();
  const [cameraOpen, setCameraOpen] = useState(false);
  const cameraRef = useRef<CameraView | null>(null);
  const [loading, setLoading] = useState(false);

  
  
  
  const tirarFoto = async () => {
    if (cameraRef.current) {
      setLoading(true);
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.7
        });
        
        console.log("Foto tirada, enviando cadastro...");
        setCameraOpen(false);

        const formData = new FormData();
        
        formData.append("nome", "Aluno Teste");
        formData.append("email", "aluno@teste.com");
        formData.append("ra", "RA12345");
        formData.append("turma_id", "74d2725d-b7f2-41f7-bab2-76f7cef2271f"); 

        // Tratamento para Web vs Mobile no React Native
        const responseImage = await fetch(photo.uri);
        const blob = await responseImage.blob();
        
        formData.append("foto", blob, "cadastro.jpg");

        const response = await apiPostFormData("/alunos/cadastrar", formData);
        Alert.alert("Sucesso!", "Sua face foi cadastrada no sistema!");
        router.back();
      } catch (error: any) {
        Alert.alert("Erro", error.message || "Erro ao cadastrar face");
      } finally {
        setLoading(false);
      }
    }
  };

  if (!permission) {
    return <View />;
  }

  if (!permission.granted) {
    requestPermission();
  }

  return (
    <View style={styles.container}>

      {cameraOpen ? (

        <View style={{ flex: 1 }}>

          <CameraView
            style={{ flex: 1 }}
            facing="front"
            ref={cameraRef}
          />

          <View style={styles.cameraControls}>

            <TouchableOpacity onPress={() => setCameraOpen(false)}>
              <Ionicons name="close" size={38} color="#fff" />
            </TouchableOpacity>

            <TouchableOpacity onPress={tirarFoto}>
              <Ionicons name="camera" size={48} color="#fff" />
            </TouchableOpacity>

          </View>

        </View>

      ) : (

        <>
          {/* HEADER */}
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()}>
              <Ionicons name="arrow-back" size={22} color="#333" />
            </TouchableOpacity>

            <Text style={styles.headerTitle}>Registrar Presença</Text>

            <View style={{ width: 22 }} />
          </View>

          {/* CARD CÂMERA */}
          <View style={styles.cameraCard}>
            <MaterialCommunityIcons
              name="face-recognition"
              size={60}
              color="#6F7682"
            />

            <Text style={styles.cameraText}>
              Posicione seu rosto na tela e siga as Instruções
            </Text>

            <Text style={styles.verifyText}>Verificar face</Text>

            <View style={styles.readyContainer}>
              <Ionicons name="checkmark-circle" size={20} color="#22C55E" />
              <Text style={styles.readyText}>Pronto para cadastrar</Text>
            </View>
          </View>

          {/* INSTRUÇÕES */}
          <View style={styles.instructionsCard}>
            <Text style={styles.instructionsTitle}>
              Instruções de check-in facial:
            </Text>

            <View style={styles.instructionItem}>
              <Ionicons name="checkmark-circle" size={20} color="#22C55E" />
              <Text style={styles.instructionText}>
                Garanta uma boa iluminação
              </Text>
            </View>

            <View style={styles.instructionItem}>
              <Ionicons name="checkmark-circle" size={20} color="#22C55E" />
              <Text style={styles.instructionText}>
                Remova óculos ou acessórios
              </Text>
            </View>

            <View style={styles.instructionItem}>
              <Ionicons name="checkmark-circle" size={20} color="#22C55E" />
              <Text style={styles.instructionText}>
                Olhe diretamente para a câmera
              </Text>
            </View>
          </View>

          {/* BOTÃO */}
          <TouchableOpacity
            style={styles.button}
            onPress={() => setCameraOpen(true)}
          >
            <Feather name="camera" size={18} color="#fff" />
            <Text style={styles.buttonText}>Cadastrar Face</Text>
          </TouchableOpacity>

        </>
      )}

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    flex: 1,
    backgroundColor: "#E9EAEC",
    paddingHorizontal: 20,
    paddingTop: 55,
    paddingBottom: 25,
    justifyContent: "space-between",
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  headerTitle: {
    fontSize: 17,
    fontWeight: "600",
    color: "#2C2C2C",
  },

  cameraCard: {
    height: 320,
    backgroundColor: "#D9DBDF",
    borderRadius: 18,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 20,
  },

  cameraText: {
    marginTop: 18,
    fontSize: 15,
    color: "#5F6773",
    textAlign: "center"
  },

  verifyText: {
    marginTop: 10,
    fontSize: 16,
    fontWeight: "600",
    color: "#B0B5BD",
  },

  readyContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 6,
  },

  readyText: {
    marginLeft: 6,
    fontSize: 14,
    color: "#22C55E",
  },

  instructionsCard: {
    backgroundColor: "#F4F4F5",
    borderRadius: 16,
    padding: 18,
  },

  instructionsTitle: {
    fontWeight: "600",
    marginBottom: 14,
    fontSize: 15,
    color: "#3F3F46",
  },

  instructionItem: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },

  instructionText: {
    marginLeft: 8,
    fontSize: 14,
    color: "#3F3F46",
  },

  button: {
    backgroundColor: "#22C55E",
    height: 52,
    borderRadius: 26,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
    gap: 8,

    shadowColor: "#22C55E",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },

  buttonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
  },

  cameraControls: {
    position: "absolute",
    bottom: 70,
    width: "100%",
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
  },

});