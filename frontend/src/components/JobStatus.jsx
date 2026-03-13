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
      {job.errorMessage ? (
        <p className="status-row error-text">
          <strong>Error:</strong> {job.errorMessage}
        </p>
      ) : null}
    </div>
  );
}
