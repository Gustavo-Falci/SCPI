// Atualize API_URL para o endereço do seu backend antes de fazer deploy
export const API_URL = window.__SCPI_API_URL__ || 'http://localhost:8000';

export const SLOTS_MATUTINO = [
  { slot: 1, inicio: '07:40', fim: '08:30' },
  { slot: 2, inicio: '08:30', fim: '09:20' },
  { slot: 3, inicio: '09:30', fim: '10:20' },
  { slot: 4, inicio: '10:20', fim: '11:10' },
  { slot: 5, inicio: '11:20', fim: '12:10' },
  { slot: 6, inicio: '12:10', fim: '13:00' },
];

export const SLOTS_NOTURNO = [
  { slot: 1, inicio: '18:45', fim: '19:35' },
  { slot: 2, inicio: '19:35', fim: '20:25' },
  { slot: 3, inicio: '20:25', fim: '21:15' },
  { slot: 4, inicio: '21:25', fim: '22:15' },
  { slot: 5, inicio: '22:15', fim: '23:05' },
];

export const DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];

export const SEMESTRES = ['1', '2', '3', '4', '5', '6'];

export const PERIODOS = ['2025-1', '2025-2', '2026-1', '2026-2'];

export const TURNOS = ['Matutino', 'Noturno'];
