/**
 * Login page — username/password form, redirects to dashboard on success.
 */
import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { InputText } from 'primereact/inputtext';
import { Password } from 'primereact/password';
import { Button } from 'primereact/button';
import { useAppDispatch, useAppSelector } from '@app/store';
import { login } from '../store/authSlice';

export const LoginPage = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { isLoading, error } = useAppSelector((state) => state.auth);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const result = await dispatch(login({ username, password }));
    if (login.fulfilled.match(result)) {
      navigate('/dashboard');
    }
  };

  return (
    <div
      className="flex align-items-center justify-content-center min-h-screen"
      style={{ background: 'linear-gradient(135deg, var(--color-primary-hover) 0%, var(--color-primary) 100%)' }}
    >
      <div className="em-login-card p-5 w-full" style={{ maxWidth: '420px' }}>
        <div className="text-center mb-5">
          <div
            className="inline-flex align-items-center justify-content-center border-round-lg mb-3"
            style={{ width: '64px', height: '64px', background: 'var(--color-primary)' }}
          >
            <i className="pi pi-shield text-white text-3xl" />
          </div>
          <h1 className="text-2xl font-bold text-900 mb-1">R &amp; D LIMS</h1>
          <p className="text-500 text-sm">Laboratory Information Management System</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-column gap-3">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-700 mb-1">
              Username
            </label>
            <InputText
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full"
              placeholder="Enter username"
              required
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-700 mb-1">
              Password
            </label>
            <Password
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full"
              inputClassName="w-full"
              feedback={false}
              placeholder="Enter password"
              required
            />
          </div>
          {error && (
            <div className="p-2 border-round bg-red-50 text-red-700 text-sm">{error}</div>
          )}
          <Button type="submit" label="Sign In" loading={isLoading} className="w-full mt-2" />
        </form>

        <p className="text-center text-xs text-400 mt-4">21 CFR Part 11 Compliant • GxP Validated</p>
      </div>
    </div>
  );
};
