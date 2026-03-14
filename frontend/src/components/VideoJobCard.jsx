import React from 'react';
import ClipCard from './ClipCard';
import JobStatus from './JobStatus';

function isActive(video) {
  return video.status === 'queued' || video.status === 'processing';
}

export default function VideoJobCard({
  video,
  selectedClipIds,
  onToggleClip,
  onDiscardClip,
  discardingClipId,
}) {
  const selectedCount = (video.clips || []).filter((clip) => selectedClipIds.includes(clip.clipId)).length;
  const completed = video.status === 'completed';

  return (
    <section className="video-card">
      <div className="video-card-header">
        <div>
          <h3>{video.originalFilename}</h3>
          <p className="video-meta">Player {video.playerName} - Video {video.videoId}</p>
        </div>
      </div>

      <JobStatus job={video} />

      {completed ? (
        <div className="video-toolbar">
          <p className="helper-text">
            {video.clips.length > 0
              ? `${video.clips.length} clip${video.clips.length === 1 ? '' : 's'} ready in S3.`
              : 'No clips remain for this video.'}
          </p>
          {selectedCount > 0 ? (
            <p className="helper-text">
              {selectedCount} selected from this video.
            </p>
          ) : null}
        </div>
      ) : null}

      {video.errorMessage ? <p className="error-text">{video.errorMessage}</p> : null}

      {completed && video.clips.length > 0 ? (
        <div className="clips-grid">
          {video.clips.map((clip) => (
            <ClipCard
              key={clip.clipId}
              clip={clip}
              selected={selectedClipIds.includes(clip.clipId)}
              onToggleSelect={(checked) => onToggleClip(clip.clipId, checked)}
              onDiscard={() => onDiscardClip(clip.clipId)}
              discarding={discardingClipId === clip.clipId}
            />
          ))}
        </div>
      ) : null}

      {completed && video.clips.length === 0 ? (
        <p className="helper-text video-empty">Discarded clips disappear here as soon as they are deleted.</p>
      ) : null}

      {isActive(video) ? (
        <p className="helper-text video-waiting">
          This card will stay pinned here while processing, then slide down into your saved list when it finishes.
        </p>
      ) : null}
    </section>
  );
}
