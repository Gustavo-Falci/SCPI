export const SLOTS_MATUTINO = [
  { id: 1, inicio: '07:40', fim: '08:30' },
  { id: 2, inicio: '08:30', fim: '09:20' },
  { id: 3, inicio: '09:30', fim: '10:20' },
  { id: 4, inicio: '10:20', fim: '11:10' },
  { id: 5, inicio: '11:20', fim: '12:10' },
  { id: 6, inicio: '12:10', fim: '13:00' },
];

export const SLOTS_NOTURNO = [
  { id: 1, inicio: '18:45', fim: '19:35' },
  { id: 2, inicio: '19:35', fim: '20:25' },
  { id: 3, inicio: '20:25', fim: '21:15' },
  { id: 4, inicio: '21:25', fim: '22:15' },
  { id: 5, inicio: '22:15', fim: '23:05' },
];

export const getSlots = (turno) => (turno === 'Noturno' ? SLOTS_NOTURNO : SLOTS_MATUTINO);

export const DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];
