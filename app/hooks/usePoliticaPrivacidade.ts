import { useCallback, useEffect, useState } from "react";

import { apiGet } from "../services/api";

export type Politica = {
  versao: string;
  data_vigencia: string;
  url: string;
};

/**
 * Busca a versão vigente da política de privacidade.
 *
 * Falha fechada de propósito: sem política carregada o consentimento não é
 * informado, então a tela que consome este hook deve manter o aceite bloqueado
 * enquanto `politica` for null.
 */
export function usePoliticaPrivacidade() {
  const [politica, setPolitica] = useState<Politica | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    setErro(null);
    try {
      const resp = await apiGet("/politica-privacidade");
      setPolitica(resp);
    } catch {
      setPolitica(null);
      setErro("Não foi possível carregar a política de privacidade.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  return { politica, loading, erro, recarregar: carregar };
}
