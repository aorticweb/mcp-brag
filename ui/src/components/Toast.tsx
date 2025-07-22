import React from 'react';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export const Toast: React.FC = () => {
  return (
    <ToastContainer
      position="bottom-right"
      autoClose={5000}
      hideProgressBar={false}
      newestOnTop={true}
      closeOnClick={true}
      rtl={false}
      pauseOnFocusLoss={false}
      draggable={true}
      pauseOnHover={false}
      theme="dark"
      style={{
        zIndex: 9999,
      }}
      toastClassName={() =>
        'relative flex p-4 min-h-10 rounded-xl justify-between overflow-hidden cursor-pointer bg-background-elevated backdrop-blur-xl border border-border shadow-lg mb-3'
      }
      bodyClassName={() => 'text-sm font-medium text-foreground flex items-center'}
      progressClassName="bg-primary"
      closeButton={false}
      enableMultiContainer={false}
    />
  );
};
