import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppLayout } from './components/AppLayout';
import { BackendHealthProvider } from './contexts/BackendHealthContext';
import './index.css';

// Ensure dark mode is always active
document.documentElement.classList.add('dark');

// Add smooth transitions on theme changes
document.documentElement.style.transition = 'background-color 0.3s ease';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BackendHealthProvider>
      <AppLayout />
    </BackendHealthProvider>
  </React.StrictMode>
);
