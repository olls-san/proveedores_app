import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  // Eliminado: fetchSales (endpoint legacy no usado)
  // Eliminado: createConciliation (la conciliación no está implementada en esta versión)
  listConciliations,
  getInventory,
  getCurrentUser,
  fetchSalesPeriod,
} from '../services/api';
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface ProductRow {
  productId: string;
  name: string;
  /** Unidades vendidas en el periodo */
  quantity: number;
  /** Monto total recaudado por este producto en el periodo */
  totalAmount: number;
  /** Código ISO o texto de la moneda, si lo provee Tecopos */
  currency?: string | null;
}

interface ConciliationItem {
  id: number;
  range_label: string;
  orders: number;
  sales_qty: number;
  revenue: number;
  discounts: number;
  total: number;
  created_at: string;
}

interface InventoryItem {
  product_id: number;
  name: string;
  total_quantity: number;
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  // Ya no se solicita el ID de proveedor manualmente.
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState<ProductRow[]>([]);
  const [totalSales, setTotalSales] = useState(0);
  const [totalUnits, setTotalUnits] = useState(0);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [conciliations, setConciliations] = useState<ConciliationItem[]>([]);
  const [me, setMe] = useState<any>(null);
  const [error, setError] = useState('');

  // Load current user on mount to prefill supplierId
  useEffect(() => {
    (async () => {
      try {
        const user = await getCurrentUser();
        setMe(user);
      } catch (err) {
        // If token invalid, redirect to login
        navigate('/login');
      }
    })();
  }, [navigate]);

  // Load conciliations on mount and whenever saleId changes
  useEffect(() => {
    (async () => {
      try {
        const data = await listConciliations();
        setConciliations(data);
      } catch (err) {
        console.error(err);
      }
    })();
  }, []);

  const handleFetchSales = async () => {
    if (!dateFrom || !dateTo) {
      setError('Debe completar las fechas.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const response = await fetchSalesPeriod(dateFrom, dateTo);
      // Mapear los items al formato esperado
      const items: ProductRow[] = (response.data || []).map((it: any) => ({
        productId: it.product_id,
        name: it.product_name,
        quantity: it.quantity,
        totalAmount: it.total_amount,
        currency: it.currency,
      }));
      // Ordenar por cantidad descendente
      setProducts(items.sort((a, b) => b.quantity - a.quantity));
      setTotalSales(response.total_sales);
      setTotalUnits(response.total_units);
      // Cargar inventario (opcional)
      const inv = await getInventory();
      setInventory(inv);
    } catch (err: any) {
      setError('Error al obtener ventas.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConciliation = async () => {
    // La lógica de conciliación requiere datos agregados, no implementada en esta versión.
  };

  return (
    <div className="container">
      <h1>Dashboard del Proveedor</h1>
      <div style={{ marginBottom: '1rem' }}>
        {/* Ya no es necesario introducir un ID de proveedor manualmente */}
        <label htmlFor="dateFrom">Desde</label>
        <input
          id="dateFrom"
          type="datetime-local"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />
        <label htmlFor="dateTo">Hasta</label>
        <input
          id="dateTo"
          type="datetime-local"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button onClick={handleFetchSales} disabled={loading}>
          {loading ? 'Consultando...' : 'Consultar ventas'}
        </button>
        {/* La funcionalidad de conciliación no está disponible en esta versión */}
      </div>
      {/* Summary metrics */}
      {products.length > 0 && (
        <div className="summary-cards">
          <div className="card">
            <h3>Productos con venta</h3>
            <p>{products.length}</p>
          </div>
          <div className="card">
            <h3>Unidades vendidas</h3>
            <p>{totalUnits}</p>
          </div>
          <div className="card">
            <h3>Ingresos</h3>
            <p>{totalSales.toFixed(2)}</p>
          </div>
          <div className="card">
            <h3>Precio promedio</h3>
            <p>{totalUnits > 0 ? (totalSales / totalUnits).toFixed(2) : '0'}</p>
          </div>
        </div>
      )}
      {/* Products table */}
      {products.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <h2>Productos vendidos</h2>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Unidades vendidas</th>
                <th>Monto total</th>
                <th>Moneda</th>
              </tr>
            </thead>
            <tbody>
              {products.map((prod) => (
                <tr key={prod.productId}>
                  <td>{prod.productId}</td>
                  <td>{prod.name}</td>
                  <td>{prod.quantity}</td>
                  <td>{prod.totalAmount.toFixed(2)}</td>
                  <td>{prod.currency || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {/* Inventory list */}
      {inventory.length > 0 && (
        <div>
          <h2>Inventario de producto</h2>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Producto</th>
                <th>Total unidades</th>
              </tr>
            </thead>
            <tbody>
              {inventory.map((item) => (
                <tr key={item.product_id}>
                  <td>{item.product_id}</td>
                  <td>{item.name}</td>
                  <td>{item.total_quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {/* Conciliations chart */}
      {conciliations.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Histórico de conciliaciones</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={conciliations.map((c) => ({ ...c, date: c.range_label }))}>
              <CartesianGrid stroke="#ccc" strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="revenue" stroke="#0d6efd" />
              <Line type="monotone" dataKey="sales_qty" stroke="#198754" />
            </LineChart>
          </ResponsiveContainer>
          {/* Conciliations table */}
          <table>
            <thead>
              <tr>
                <th>Rango</th>
                <th>Órdenes</th>
                <th>Unidades</th>
                <th>Ingresos</th>
                <th>Descuentos</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {conciliations.map((c) => (
                <tr key={c.id}>
                  <td>{c.range_label}</td>
                  <td>{c.orders}</td>
                  <td>{c.sales_qty}</td>
                  <td>{c.revenue.toFixed(2)}</td>
                  <td>{c.discounts.toFixed(2)}</td>
                  <td>{c.total.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;