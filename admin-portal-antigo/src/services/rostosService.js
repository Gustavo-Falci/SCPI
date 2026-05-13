import { apiClient } from './apiClient';

export const listarRostosRekognition = () =>
  apiClient.get('/admin/rostos/rekognition').then((r) => r.data);

export const listarRostosS3 = () =>
  apiClient.get('/admin/rostos/s3').then((r) => r.data);

export const excluirRostoRekognition = (face_id) =>
  apiClient.delete(`/admin/rostos/rekognition/${face_id}`).then((r) => r.data);

export const excluirRostosRekognitionBulk = (face_ids) =>
  apiClient.delete('/admin/rostos/rekognition/bulk', { data: { face_ids } }).then((r) => r.data);

export const excluirRostoS3 = (key) =>
  apiClient.delete('/admin/rostos/s3', { data: { key } }).then((r) => r.data);
