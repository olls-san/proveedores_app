import axios from 'axios';

// Create an Axios instance with sensible defaults. You can extend this to
// automatically include the Authorization header when a token is present.
const apiClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the JWT token when available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers = config.headers ?? {};
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Authentication
export async function login(email: string, password: string) {
  // The FastAPI OAuth2PasswordRequestForm expects fields named ``username`` and ``password``.
  const params = new URLSearchParams();
  params.append('username', email);
  params.append('password', password);
  const response = await apiClient.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return response.data;
}

export async function register(
  email: string,
  password: string,
  name: string,
  supplierId: number,
) {
  const response = await apiClient.post('/auth/register', {
    email,
    password,
    name,
    supplierIdTecopos: supplierId,
  });
  return response.data;
}

// Sales
export async function fetchSales(
  dateFrom: string,
  dateTo: string,
  supplierId: number,
) {
  const response = await apiClient.get('/sales', {
    params: { dateFrom, dateTo, supplierId },
  });
  return response.data;
}

// Conciliations
export async function createConciliation(saleId: number) {
  const response = await apiClient.post('/conciliations', { sale_id: saleId });
  return response.data;
}

export async function listConciliations() {
  const response = await apiClient.get('/conciliations');
  return response.data;
}

// Inventory
export async function getInventory() {
  const response = await apiClient.get('/inventory');
  return response.data;
}

// Current user
export async function getCurrentUser() {
  const response = await apiClient.get('/me');
  return response.data;
}