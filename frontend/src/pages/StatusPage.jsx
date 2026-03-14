import React from 'react';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import JobStatus from '../components/JobStatus';
import { getJobStatus } from '../api/client';

export default function StatusPage() {
  const { jobId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [job, setJob] = useState({
    jobId: Number(jobId),
    videoId: location.state?.videoId || null,
    status: 'queued',
    errorMessage: null,
  });
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function fetchStatus() {
      try {
        const data = await getJobStatus(jobId);
        if (!active) {
          return;
        }

        setJob(data);

        if (data.status === 'completed' && data.videoId) {
          navigate(`/videos/${data.videoId}/clips`);
        }
      } catch (err) {
        if (active) {
          setError(err.message);
        }
      }
    }

    fetchStatus();
    const timer = setInterval(fetchStatus, 3000);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [jobId, navigate]);

  return (
    <div>
      <h2>Job Status</h2>
      <p className="section-lead">Polling the local helper every 3 seconds until the local clip build finishes.</p>
      <JobStatus job={job} />
      {error ? <p className="error-text">{error}</p> : null}
    </div>
  );
}
