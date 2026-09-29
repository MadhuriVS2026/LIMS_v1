/**
 * Root Application component — wraps the app with all necessary providers.
 */
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PrimeReactProvider } from 'primereact/api';
import { store } from '@app/store';
import { AppRouter } from '@app/router/AppRouter';
import { ToastHost } from '@shared/components/ToastHost';
import { getErrorMessage, toastService } from '@shared/services/toastService';

// Global mutation/query error handling: any failed API call anywhere in the
// app surfaces a toast automatically, so actions never fail silently.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
  queryCache: new QueryCache({
    onError: (error) => toastService.error(getErrorMessage(error), 'Failed to load data'),
  }),
  mutationCache: new MutationCache({
    onError: (error) => toastService.error(getErrorMessage(error), 'Action failed'),
  }),
});

export const App = () => {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <PrimeReactProvider>
          <BrowserRouter>
            <ToastHost />
            <AppRouter />
          </BrowserRouter>
        </PrimeReactProvider>
      </QueryClientProvider>
    </Provider>
  );
};
