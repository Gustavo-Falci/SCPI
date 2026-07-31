import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as WebBrowser from "expo-web-browser";

import { Colors } from "../../constants/theme";
import type { Politica } from "../../hooks/usePoliticaPrivacidade";

type Props = {
  checked: boolean;
  onToggle: () => void;
  politica: Politica | null;
  loading: boolean;
  erro: string | null;
  onRecarregar: () => void;
  /**
   * Data ISO do aceite vigente, quando o aluno já consentiu com ESTA versão da
   * política. Presente = card vira informativo, sem checkbox.
   */
  aceiteVigenteEm?: string | null;
};

/**
 * Card de consentimento LGPD usado no primeiro acesso e no cadastro facial.
 *
 * Compartilhado entre as duas telas de propósito: o texto é peça jurídica e
 * precisa ser idêntico nos dois fluxos.
 */
export function ConsentCard({
  checked,
  onToggle,
  politica,
  loading,
  erro,
  onRecarregar,
  aceiteVigenteEm,
}: Props) {
  if (loading) {
    return (
      <View style={styles.consentCard}>
        <ActivityIndicator color={Colors.brand.primary} />
      </View>
    );
  }

  // Sem política carregada não há consentimento informado — não dá para aceitar.
  if (erro || !politica) {
    return (
      <View style={styles.consentCard}>
        <Text style={styles.consentBody}>{erro ?? "Política indisponível."}</Text>
        <TouchableOpacity
          onPress={onRecarregar}
          activeOpacity={0.8}
          accessibilityRole="button"
          accessibilityLabel="Tentar carregar a política novamente"
        >
          <Text style={styles.retryText}>Tentar novamente</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Consentimento vigente já registrado: nada a coletar, só informar. Exibir um
  // checkbox aqui seria pedir de novo algo que o aluno já deu — e pré-marcá-lo
  // valeria como consentimento por omissão, vedado pelo Art. 8º §4º.
  if (aceiteVigenteEm) {
    return (
      <View style={[styles.consentCard, styles.consentCardActive]}>
        <View style={styles.consentHeader}>
          <Ionicons name="shield-checkmark" size={22} color="#1DB954" />
          <Text style={styles.consentTitle}>Consentimento ativo</Text>
        </View>
        <Text style={styles.consentBody}>
          Você autorizou o uso da sua imagem facial para{" "}
          <Text style={styles.consentBodyStrong}>controle de presença nas aulas</Text> em{" "}
          {new Date(aceiteVigenteEm).toLocaleString("pt-BR")}, conforme a versão{" "}
          {politica.versao} da política. Pode revogar a qualquer momento pelo seu perfil.{" "}
          <Text
            style={styles.link}
            onPress={() => WebBrowser.openBrowserAsync(politica.url)}
          >
            Ver Política de Privacidade.
          </Text>
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.consentCard, checked && styles.consentCardActive]}>
      <View style={styles.consentHeader}>
        <Ionicons name="shield-checkmark-outline" size={22} color={Colors.brand.primary} />
        <Text style={styles.consentTitle}>Consentimento LGPD</Text>
      </View>
      <Text style={styles.consentBody}>
        Autorizo o SCPI a coletar e processar minha imagem facial para{" "}
        <Text style={styles.consentBodyStrong}>controle de presença nas aulas</Text>{" "}
        (LGPD Art. 11, II, &apos;a&apos;). Dados armazenados em servidores AWS (us-east-1, EUA)
        sob o DPA da AWS — LGPD Art. 33, II. O aceite é registrado com data, hora e endereço
        IP para fins de comprovação. Posso revogar este consentimento a qualquer momento pelo
        meu perfil.{" "}
        <Text
          style={styles.link}
          onPress={() => WebBrowser.openBrowserAsync(politica.url)}
        >
          Ver Política de Privacidade (versão {politica.versao}).
        </Text>
      </Text>
      <TouchableOpacity
        style={styles.consentRow}
        onPress={onToggle}
        activeOpacity={0.8}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <View style={[styles.checkbox, checked && styles.checkboxActive]}>
          {checked && <Ionicons name="checkmark" size={16} color="#fff" />}
        </View>
        <Text style={styles.consentCheckLabel}>
          Li e concordo com o tratamento dos meus dados biométricos.
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
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
  link: { color: Colors.brand.primary, textDecorationLine: "underline" },
  retryText: { color: Colors.brand.primary, marginTop: 8, fontWeight: "600" },
});
