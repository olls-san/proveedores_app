import axios from 'axios';

const rawBase = import.meta.env.VITE_API_BASE?.trim();

// Normaliza: quita slash al final
const baseURL = rawBase ? rawBase.replace(/\/+$/, '') : '';

if (!baseURL) {
  // Ayuda visual en tiempo de desarrollo / build
  // (no detiene la app, pero deja claro el problema)
  // eslint-disable-next-line no-console
  console.warn(
    '[API] VITE_API_BASE no está definido. Las peticiones irán al mismo origen del frontend y fallarán en producción.'
  );
}

export const api = axios.create({
  baseURL, // ejemplo: https://proveedores-backend.onrender.com
  // timeout: 20000, // opcional
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});

// Helpers de endpoints (ajusta si tu backend tiene prefijo /api)
export async function login(email: string, password: string) {
  const { data } = await api.post('/auth/login', { email, password });
  return data; // { access_token, token_type }
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
    supplierIdTecopos, // coincide con el backend
  });
  return data;
}

export async function me() {
  const { data } = await api.get('/me');
  return data;
}

export async function getConciliations() {
  const { data } = await api.get('/conciliations');
  return data;
}

export async function getSales(params: {
  dateFrom: string;
  dateTo: string;
  status?: string;
}) {
  const { data } = await api.get('/sales', { params });
  return data;
}
