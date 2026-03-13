import React from 'react';

export default function ClipCard({ clip, bucket }) {
  const thumbnailUrl = `https://${bucket}.s3.amazonaws.com/${clip.thumbnailKey}`;
  const clipUrl = `https://${bucket}.s3.amazonaws.com/${clip.clipKey}`;

  return (
    <article className="clip-card">
      <img
        src={thumbnailUrl}
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
      <a href={clipUrl} target="_blank" rel="noreferrer" className="secondary-button">
        Open Clip
      </a>
    </article>
  );
}
