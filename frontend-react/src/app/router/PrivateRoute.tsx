/**
 * PrivateRoute — redirects unauthenticated users to /login.
 * Verifies session by re-fetching the current user on first mount.
 */
import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@app/store';
import { fetchCurrentUser } from '@features/authentication/store/authSlice';
import { storageService } from '@shared/services/storageService';

export const PrivateRoute = () => {
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = storageService.getAccessToken();
    if (token && !isAuthenticated) {
      dispatch(fetchCurrentUser()).finally(() => setChecked(true));
    } else {
      setChecked(true);
    }
  }, [dispatch, isAuthenticated]);

  if (!checked) return null;

  const token = storageService.getAccessToken();
  if (!token) return <Navigate to="/login" replace />;

  return <Outlet />;
};
