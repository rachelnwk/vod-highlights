import React from 'react';

export default function UploadForm({
  file,
  playerName,
  onFileChange,
  onPlayerNameChange,
  onSubmit,
  loading,
  error,
  statusText,
  uploadProgress,
}) {
  return (
    <form onSubmit={onSubmit} className="upload-form">
      <label className="field-label">
        Video (.mp4, .mov, or .mkv)
        <input
          type="file"
          accept=".mp4,.mov,.mkv,video/mp4,video/quicktime,video/x-matroska"
          className="field-input"
          onChange={(e) => onFileChange(e.target.files?.[0] || null)}
          required
        />
      </label>

      <label className="field-label">
        Player Name
        <input
          type="text"
          value={playerName}
          onChange={(e) => onPlayerNameChange(e.target.value)}
          placeholder="RachelLi"
          className="field-input"
          required
        />
      </label>

      <p className="helper-text">Maximum upload size: 300 MB.</p>
      {file ? <p className="helper-text">Selected file: {file.name}</p> : null}
      {loading && statusText ? (
        <p className="helper-text">
          {statusText}
          {uploadProgress > 0 ? ` (${uploadProgress}%)` : ''}
        </p>
      ) : null}
      {error ? <p className="error-text">{error}</p> : null}

      <button type="submit" className="primary-button" disabled={loading}>
        {loading ? 'Uploading...' : 'Upload and Start Processing'}
      </button>
    </form>
  );
}
