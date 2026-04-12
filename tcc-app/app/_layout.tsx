import { ThemeProvider, DarkTheme, DefaultTheme } from '@react-navigation/native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { storage } from '../services/storage';
import { useEffect, useState } from 'react';
import { useColorScheme } from '@/hooks/use-color-scheme';

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const router = useRouter();
  const segments = useSegments();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = await storage.getItem('access_token');
        const role = await storage.getItem('user_role');
        const inAuthGroup = segments[0] === 'auth';
        
        // Se NÃO tem token e NÃO está na página de login, manda pro login
        if (!token && !inAuthGroup) {
          router.replace('/auth/login');
        } 
        // Se TEM token e está tentando acessar a página de login, manda pra home correta
        else if (token && inAuthGroup) {
          if (role === 'Professor') {
             router.replace('/professor/home');
          } else {
             router.replace('/aluno/home');
          }
        }
      } catch (e) {
        console.warn(e);
      } finally {
        setIsReady(true);
      }
    };

    // Timeout zero para garantir que o root layout foi montado antes de rotear
    setTimeout(() => {
       checkAuth();
    }, 0);
  }, [segments]);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="auth/login" options={{ headerShown: false }} />
        <Stack.Screen name="aluno/home" options={{ headerShown: false }} />
        <Stack.Screen name="aluno/cadastro-facial" options={{ headerShown: false }} />
        <Stack.Screen name="professor/home" options={{ headerShown: false }} />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}
