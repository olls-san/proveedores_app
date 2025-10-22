import axios from 'axios';

const rawBase = import.meta.env.VITE_API_BASE?.trim();
const baseURL = rawBase ? rawBase.replace(/\/+$/, '') : '';

if (!baseURL) {
  console.warn('[API] VITE_API_BASE no está definido. Las peticiones usarán el mismo origen.');
}

export const api = axios.create({ baseURL });

// Inyecta token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});

// ===== AUTH =====
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

export async function me() {
  const { data } = await api.get('/me'); // si tu backend usa prefijo, cambia a '/api/me'
  return data;
}

// Alias para no tocar Dashboard.tsx
export async function getCurrentUser() {
  return me();
}

// ===== DATA =====
export async function listConciliations() {
  const { data } = await api.get('/conciliations'); // o '/api/conciliations'
  return data;
}

export async function getInventory() {
  const { data } = await api.get('/inventory'); // o '/api/inventory'
  return data;
}

// Nombre “oficial”
export async function getSales(params: {
  dateFrom: string;
  dateTo: string;
  supplierId: number;
  status?: string;
}) {
  // When calling the sales endpoint we need to supply the supplierId and date range
  // Example backend URL: /sales?dateFrom=2025-10-01%2000:00&dateTo=2025-10-19%2000:00&supplierId=362
  const { dateFrom, dateTo, supplierId, ...rest } = params;
  const query = { dateFrom, dateTo, supplierId, ...rest };
  const { data } = await api.get('/sales', { params: query }); // or '/api/sales'
  return data;
}

/**
 * Alias to fetch sales data using positional arguments.
 *
 * The dashboard calls `fetchSales(dateFrom, dateTo, supplierId)`,
 * so we provide this helper to bridge that call signature.
 */
export async function fetchSales(
  dateFrom: string,
  dateTo: string,
  supplierId: number,
  status?: string
) {
  return getSales({ dateFrom, dateTo, supplierId, status });
}

/**
 * Create a conciliation entry for a given sale ID.
 *
 * This calls the POST /conciliations endpoint on the backend.
 *
 * @param saleId The ID of the sale record to consolidate.
 */
export async function createConciliation(saleId: number) {
  const { data } = await api.post('/conciliations', { sale_id: saleId });
  return data;
}
