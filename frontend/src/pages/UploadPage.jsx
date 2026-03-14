import React from 'react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import UploadForm from '../components/UploadForm';
import { completeUpload, getPresignedUploadUrl } from '../api/client';

const MAX_UPLOAD_BYTES = 300 * 1024 * 1024;
const MAX_UPLOAD_MB = Math.round(MAX_UPLOAD_BYTES / (1024 * 1024));

function uploadFileToS3(uploadUrl, file, contentType, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', uploadUrl);

    if (contentType) {
      xhr.setRequestHeader('Content-Type', contentType);
    }

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }
      onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onerror = () => {
      reject(
        new Error(
          'S3 upload failed before the browser received a response. Check the browser Network tab for the PUT request.'
        )
      );
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress(100);
        resolve();
        return;
      }

      reject(
        new Error(
          `Failed to upload file to S3 (status ${xhr.status}${
            xhr.responseText ? `: ${xhr.responseText.slice(0, 200)}` : ''
          }).`
        )
      );
    };

    xhr.send(file);
  });
}

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
      const lowerName = file.name.toLowerCase();
      const fallbackType = lowerName.endsWith('.mp4')
        ? 'video/mp4'
        : lowerName.endsWith('.mkv')
        ? 'video/x-matroska'
        : 'video/quicktime';
      const contentType = file.type || fallbackType;
      setStatusText('Requesting upload URL...');
      const presign = await getPresignedUploadUrl(file.name, contentType, file.size);

      setStatusText('Uploading video to S3...');
      await uploadFileToS3(presign.uploadUrl, file, contentType, setUploadProgress);

      setStatusText('Queueing processing job...');
      const complete = await completeUpload(file.name, presign.s3Key, playerName.trim());
      navigate(`/status/${complete.jobId}`, {
        state: { videoId: complete.videoId },
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
        Use a 1080p `.mov`, `.mp4`, or `.mkv` for the best OCR results, then enter the player name to track.
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
