import React from 'react';

export default function ClipCard({ clip }) {
  return (
    <article className="clip-card">
      <img
        src={clip.thumbnailUrl}
        alt={`Thumbnail for clip ${clip.clipId}`}
        className="clip-thumbnail"
      />
      <p className="clip-meta">
        <strong>Clip ID:</strong> {clip.clipId}
      </p>
      <p className="clip-meta">
        <strong>Range:</strong> {clip.startTime}s - {clip.endTime}s
      </p>
      <p className="clip-meta">
        <strong>Score:</strong> {clip.score}
      </p>
      <a href={clip.clipUrl} target="_blank" rel="noreferrer" className="secondary-button">
        Open Clip
      </a>
    </article>
  );
}
