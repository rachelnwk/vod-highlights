import React from 'react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ClipCard from '../components/ClipCard';
import { getClipsForVideo } from '../api/client';

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

  return (
    <div>
      <h2>Generated Clips for Video {videoId}</h2>
      <p className="section-lead">Review the locally-cut highlight clips that were planned by AWS Lambda.</p>
      {clips.length === 0 ? <p className="helper-text">No clips found yet.</p> : null}
      <div className="clips-grid">
        {clips.map((clip) => (
          <ClipCard key={clip.clipId} clip={clip} />
        ))}
      </div>
    </div>
  );
}
