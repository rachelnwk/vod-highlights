import React from 'react';
import UploadPage from './UploadPage';

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>VOD Highlight Generator</h1>
        <p className="subtitle">Upload a VOD to extract your highlights!</p>
      </header>

      <main className="panel">
        <UploadPage />
      </main>
    </div>
  );
}
