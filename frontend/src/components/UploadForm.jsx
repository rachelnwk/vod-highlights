import React from 'react';

export default function UploadForm({
  file,
  playerName,
  onFileChange,
  onPlayerNameChange,
  onSubmit,
  loading,
  submitDisabled,
  submitDisabledMessage,
  error,
  statusText,
  uploadProgress,
  resetToken,
}) {
  const uploadInputId = `vod-file-${resetToken}`;

  return (
    <form onSubmit={onSubmit} className="upload-form">
      <div className="field-label">
        Video File
        <input
          id={uploadInputId}
          key={resetToken}
          type="file"
          accept=".mp4,.mov,.mkv,video/mp4,video/quicktime,video/x-matroska"
          className="upload-input"
          onChange={(e) => onFileChange(e.target.files?.[0] || null)}
          required
        />
        <label htmlFor={uploadInputId} className={`upload-dropzone${file ? ' has-file' : ''}`}>
          <span className="upload-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" focusable="false">
              <path
                d="M12 16V6m0 0-4 4m4-4 4 4M5 18h14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span className="upload-title">{file ? file.name : 'Choose a VOD file'}</span>
          <span className="upload-subtitle">
            {file ? 'Click here to replace the current file.' : 'Click here to upload a .mov, .mp4, or .mkv file.'}
          </span>
        </label>
      </div>

      <label className="field-label">
        Username
        <input
          type="text"
          value={playerName}
          onChange={(e) => onPlayerNameChange(e.target.value)}
          className="field-input"
          required
        />
      </label>

      {loading && statusText ? (
        <>
          <p className="helper-text">
            {statusText}
            {uploadProgress > 0 ? ` (${uploadProgress}%)` : ''}
          </p>
          <div className="progress-track upload-track" aria-hidden="true">
            <div className={`progress-fill${uploadProgress >= 100 ? ' done' : ''}`} style={{ width: `${uploadProgress}%` }} />
          </div>
        </>
      ) : null}
      {!loading && submitDisabledMessage ? <p className="helper-text">{submitDisabledMessage}</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      <button type="submit" className="primary-button upload-submit" disabled={loading || submitDisabled}>
        {loading ? 'Starting...' : 'Begin Processing'}
      </button>
    </form>
  );
}
