import React from 'react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ClipCard from '../components/ClipCard';
import { getClipsForVideo, getConfiguredBucket } from '../api/client';

const bucket = import.meta.env.VITE_S3_BUCKET || getConfiguredBucket();

export default function ClipsPage() {
  const { videoId } = useParams();
  const [clips, setClips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function fetchClips() {
      try {
        setLoading(true);
        const data = await getClipsForVideo(videoId);
        if (active) {
          setClips(Array.isArray(data) ? data : data.clips || []);
          setError('');
        }
      } catch (err) {
        if (active) {
          setError(err.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    fetchClips();

    return () => {
      active = false;
    };
  }, [videoId]);

  if (loading) {
    return <p className="section-lead">Loading clips...</p>;
  }

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  if (!bucket) {
    return (
      <p className="error-text">
        Missing S3 bucket configuration. Set `VITE_S3_BUCKET` or add the bucket to
        `frontend/client-config.ini`.
      </p>
    );
  }

  return (
    <div>
      <h2>Generated Clips for Video {videoId}</h2>
      <p className="section-lead">Review and open each generated highlight clip.</p>
      {clips.length === 0 ? <p className="helper-text">No clips found yet.</p> : null}
      <div className="clips-grid">
        {clips.map((clip) => (
          <ClipCard key={clip.clipId} clip={clip} bucket={bucket} />
        ))}
      </div>
    </div>
  );
}
