import React from 'react';
import { Route, Routes } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import StatusPage from './pages/StatusPage';
import ClipsPage from './pages/ClipsPage';

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="eyebrow">Cloud Video Pipeline</p>
        <h1>VOD Highlight Generator</h1>
        <p className="subtitle">
          Upload a match clip, detect key moments, and review generated highlights.
        </p>
      </header>

      <main className="panel">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/status/:jobId" element={<StatusPage />} />
          <Route path="/videos/:videoId/clips" element={<ClipsPage />} />
        </Routes>
      </main>
    </div>
  );
}
