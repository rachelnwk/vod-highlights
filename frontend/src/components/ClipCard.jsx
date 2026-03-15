import React from 'react';

// Render one clip preview card with selection, preview, download, and discard actions.
// Input: Props with the clip record, current selection state, and action callbacks.
// Output: JSX for a single saved clip.
export default function ClipCard({
  clip,
  selected,
  onToggleSelect,
  onDiscard,
  discarding,
}) {
  return (
    <article className="clip-card">
      <img
        src={clip.thumbnailUrl}
        alt={`Thumbnail for clip ${clip.clipId}`}
        className="clip-thumbnail"
      />
      <label className="clip-select">
        <input
          type="checkbox"
          checked={selected}
          onChange={(event) => onToggleSelect(event.target.checked)}
        />
        Select clip
      </label>
      <p className="clip-meta">
        <strong>Clip ID:</strong> {clip.clipId}
      </p>
      <p className="clip-meta">
        <strong>Range:</strong> {clip.startTime}s - {clip.endTime}s
      </p>
      <div className="clip-actions">
        <a href={clip.clipUrl} target="_blank" rel="noreferrer" className="secondary-button">
          Open Clip
        </a>
        <a
          href={clip.downloadUrl || clip.clipUrl}
          target="_blank"
          rel="noreferrer"
          className="secondary-button"
        >
          Download
        </a>
        <button type="button" className="danger-button" onClick={onDiscard} disabled={discarding}>
          {discarding ? 'Discarding...' : 'Discard'}
        </button>
      </div>
    </article>
  );
}
