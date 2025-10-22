import axios from 'axios';

const rawBase = import.meta.env.VITE_API_BASE?.trim();
const baseURL = rawBase ? rawBase.replace(/\/+$/, '') : '';

if (!baseURL) {
  console.warn('[API] VITE_API_BASE no está definido. Las peticiones usarán el mismo origen y fallarán en prod.');
}

export const api = axios.create({
  baseURL, // Ej: https://proveedores-backend.onrender.com
});

// Inyecta token si existe
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});

// ------- AUTH -------
export async function login(email: string, password: string) {
  const { data } = await api.post('/auth/login', { email, password });
  return data as { access_token: string; token_type: 'bearer' };
}

export async function register(
  email: string,
  password: string,
  name: string,
  supplierIdTecopos: number
) {
  const { data } = await api.post('/auth/register', {
    email,
    password,
    name,
    supplierIdTecopos,
  });
  return data;
}

// Antes tenías "me()"; mantenlo y añade un alias "getCurrentUser()"
export async function me() {
  const { data } = await api.get('/me'); // si tu backend usa prefijo, cambia a '/api/me'
  return data;
}

export async function getCurrentUser() {
  // Alias para que Dashboard.tsx compile
  return me();
}

// ------- DATA -------
export async function listConciliations() {
  const { data } = await api.get('/conciliations'); // o '/api/conciliations'
  return data;
}

export async function getInventory() {
  const { data } = await api.get('/inventory'); // o '/api/inventory'
  return data;
}

export async function getSales(params: {
  dateFrom: string;
  dateTo: string;
  status?: string;
}) {
  const { data } = await api.get('/sales', { params }); // o '/api/sales'
  return data;
}

