#!/usr/bin/env node
// Copia variáveis EXPO_PUBLIC_* do .env raiz para tcc-app/.env
// Metro bundler só lê .env do diretório do projeto (tcc-app/).
const fs = require('fs');
const path = require('path');

const rootEnv = path.resolve(__dirname, '../../.env');
const targetEnv = path.resolve(__dirname, '../.env');

if (!fs.existsSync(rootEnv)) {
  console.error(`Erro: .env não encontrado em ${rootEnv}`);
  console.error('Crie o arquivo .env na raiz do projeto a partir de .env.example');
  process.exit(1);
}

const expoLines = fs.readFileSync(rootEnv, 'utf8')
  .split('\n')
  .filter(line => line.startsWith('EXPO_PUBLIC_'));

if (expoLines.length === 0) {
  console.warn('Aviso: nenhuma variável EXPO_PUBLIC_* encontrada no .env raiz.');
}

fs.writeFileSync(targetEnv, expoLines.join('\n') + '\n');
console.log(`tcc-app/.env atualizado (${expoLines.length} variável(is) Expo).`);
