import React from 'react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import UploadForm from '../components/UploadForm';
import { startLocalJob } from '../api/client';

const MAX_UPLOAD_BYTES = 300 * 1024 * 1024;
const MAX_UPLOAD_MB = Math.round(MAX_UPLOAD_BYTES / (1024 * 1024));

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [playerName, setPlayerName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusText, setStatusText] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const navigate = useNavigate();

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setStatusText('');
    setUploadProgress(0);

    if (!file) {
      setError('Please select an .mp4, .mov, or .mkv file.');
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError(`Please choose a video that is ${MAX_UPLOAD_MB} MB or smaller.`);
      return;
    }

    setLoading(true);
    try {
      setStatusText('Sending video to the local helper...');
      const job = await startLocalJob(file, playerName.trim(), setUploadProgress);
      setStatusText('Starting local OCR and Lambda analysis...');
      navigate(`/status/${job.jobId}`, {
        state: { videoId: job.videoId },
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setStatusText('');
    }
  }

  return (
    <div>
      <h2>Start A Highlight Job</h2>
      <p className="section-lead">
        Pick one local 1080p `.mov`, `.mp4`, or `.mkv`, then let the local helper extract OCR before
        the compact JSON gets analyzed in AWS Lambda.
      </p>
      <UploadForm
        file={file}
        playerName={playerName}
        onFileChange={setFile}
        onPlayerNameChange={setPlayerName}
        onSubmit={handleSubmit}
        loading={loading}
        error={error}
        statusText={statusText}
        uploadProgress={uploadProgress}
      />
    </div>
  );
}
