import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { register } from '../services/api';

/**
 * Página de creación de cuenta para proveedores.
 * Permite registrar nombre, email, contraseña e ID del proveedor.
 * Tras el registro, redirige a la pantalla de login.
 */
const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [supplierId, setSupplierId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplierId) {
      setError('Debe indicar el ID de proveedor');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await register(email, password, name, Number(supplierId));
      // Se redirige a la pantalla de login al terminar
      navigate('/login', { replace: true });
    } catch {
      setError('No se pudo crear la cuenta. Verifica los datos e inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>Crear cuenta</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="name">Nombre</label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <label htmlFor="email">Correo electrónico</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <label htmlFor="supplierId">ID de Proveedor</label>
        <input
          id="supplierId"
          type="number"
          value={supplierId}
          onChange={(e) => setSupplierId(e.target.value)}
          required
        />
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Registrando...' : 'Registrar'}
        </button>
      </form>
    </div>
  );
};

export default RegisterPage;
