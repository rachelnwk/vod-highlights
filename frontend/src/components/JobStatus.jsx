import React from 'react';

// Purpose: Display status, progress, and clip count details for one job.
// Input: Props with a job object from the worker API.
// Output: JSX for the job status panel.
export default function JobStatus({ job }) {
  const tone =
    job.status === 'completed'
      ? 'ok'
      : job.status === 'failed'
      ? 'bad'
      : 'warn';
  const progress = Math.max(0, Math.min(job.progressPercent ?? 0, 100));
  const clipCount = Array.isArray(job.clips) ? job.clips.length : job.summary?.clipCount;

  return (
    <div className="status-card">
      <p className="status-row">
        <strong>Job ID:</strong> {job.jobId}
      </p>
      <p className="status-row">
        <strong>Video ID:</strong> {job.videoId}
      </p>
      <p className="status-row">
        <strong>Status:</strong>
        <span className={`status-pill ${tone}`}>{job.status}</span>
      </p>
      {job.stage ? (
        <p className="status-row">
          <strong>Stage:</strong> {job.stage.replaceAll('_', ' ')}
        </p>
      ) : null}
      {job.progressPercent !== undefined ? (
        <>
          <p className="status-row">
            <strong>Progress:</strong> {job.progressPercent}%
          </p>
          <div className="progress-track" aria-hidden="true">
            <div className={`progress-fill${progress >= 100 ? ' done' : ''}`} style={{ width: `${progress}%` }} />
          </div>
        </>
      ) : null}
      {clipCount !== undefined ? (
        <p className="status-row">
          <strong>Clips:</strong> {clipCount}
        </p>
      ) : null}
      {job.errorMessage ? (
        <p className="status-row error-text">
          <strong>Error:</strong> {job.errorMessage}
        </p>
      ) : null}
    </div>
  );
}
