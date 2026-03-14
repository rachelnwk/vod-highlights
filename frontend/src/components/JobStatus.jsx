import React from 'react';

export default function JobStatus({ job }) {
  const tone =
    job.status === 'completed'
      ? 'ok'
      : job.status === 'failed'
      ? 'bad'
      : 'warn';

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
        <p className="status-row">
          <strong>Progress:</strong> {job.progressPercent}%
        </p>
      ) : null}
      {job.summary?.matchedCount !== undefined ? (
        <p className="status-row">
          <strong>Matched Events:</strong> {job.summary.matchedCount}
        </p>
      ) : null}
      {job.summary?.clipCount !== undefined ? (
        <p className="status-row">
          <strong>Clips:</strong> {job.summary.clipCount}
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
