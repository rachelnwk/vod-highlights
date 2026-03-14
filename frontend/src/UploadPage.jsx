import React from 'react';
import { useEffect, useState } from 'react';
import UploadForm from './components/UploadForm';
import VideoJobCard from './components/VideoJobCard';
import { deleteAllVideos, discardClip, downloadMergedClips, listVideos, startLocalJob } from './client';

// Purpose: Coordinate uploads, saved videos, clip selection, and dashboard actions.
// Input: No props.
// Output: JSX for the main upload-and-library page.
export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [playerName, setPlayerName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusText, setStatusText] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [videos, setVideos] = useState([]);
  const [videosLoading, setVideosLoading] = useState(true);
  const [videosError, setVideosError] = useState('');
  const [resetToken, setResetToken] = useState(0);
  const [selectedClipIds, setSelectedClipIds] = useState([]);
  const [mergeLoading, setMergeLoading] = useState(false);
  const [deleteAllLoading, setDeleteAllLoading] = useState(false);
  const [discardingClipId, setDiscardingClipId] = useState('');
  const hasActiveVideo = videos.some((video) => video.status === 'queued' || video.status === 'processing');

  // Purpose: Refresh the saved video library from the worker and sync selected clips.
  // Input: showLoading (boolean) to control whether the loading state is shown.
  // Output: Promise that resolves after state is updated.
  async function refreshVideos(showLoading = false) {
    if (showLoading) {
      setVideosLoading(true);
    }

    try {
      const data = await listVideos();
      const nextVideos = Array.isArray(data) ? data : data.videos || [];
      setVideos(nextVideos);
      setVideosError('');
      setSelectedClipIds((previous) => {
        const availableIds = new Set(
          nextVideos.flatMap((video) => (video.clips || []).map((clip) => clip.clipId))
        );
        return previous.filter((clipId) => availableIds.has(clipId));
      });
    } catch (err) {
      setVideosError(err.message);
    } finally {
      if (showLoading) {
        setVideosLoading(false);
      }
    }
  }

  useEffect(() => {
    refreshVideos(true);
  }, []);

  useEffect(() => {
    if (!hasActiveVideo) {
      return undefined;
    }

    const timer = setInterval(() => {
      refreshVideos();
    }, 3000);

    return () => clearInterval(timer);
  }, [videos]);

  // Purpose: Add or remove a clip ID from the current cross-video selection.
  // Input: clipId (string) and checked (boolean) from the selection checkbox.
  // Output: None; updates component state.
  function updateClipSelection(clipId, checked) {
    setSelectedClipIds((previous) => {
      if (checked) {
        if (previous.includes(clipId)) {
          return previous;
        }
        return [...previous, clipId];
      }

      return previous.filter((currentClipId) => currentClipId !== clipId);
    });
  }

  // Purpose: Delete one saved clip after confirmation and refresh the library.
  // Input: videoId (string) and clipId (string) identifying the clip to discard.
  // Output: Promise that resolves after the delete flow finishes.
  async function handleDiscardClip(videoId, clipId) {
    const confirmed = window.confirm('Discard this clip from the library and delete it from S3?');
    if (!confirmed) {
      return;
    }

    setDiscardingClipId(clipId);
    try {
      await discardClip(videoId, clipId);
      await refreshVideos();
    } catch (err) {
      setVideosError(err.message);
    } finally {
      setDiscardingClipId('');
    }
  }

  // Purpose: Request a merged download for the currently selected clips.
  // Input: No direct arguments; uses selectedClipIds from state.
  // Output: Promise that resolves after the download request completes.
  async function handleMergeSelected() {
    if (selectedClipIds.length === 0) {
      return;
    }

    setMergeLoading(true);
    try {
      await downloadMergedClips(selectedClipIds);
    } catch (err) {
      setVideosError(err.message);
    } finally {
      setMergeLoading(false);
    }
  }

  // Purpose: Delete every saved video and its clips after user confirmation.
  // Input: No direct arguments; uses savedVideos from state.
  // Output: Promise that resolves after the library is cleared.
  async function handleDeleteAllVideos() {
    if (savedVideos.length === 0) {
      return;
    }

    const confirmed = window.confirm(
      `Delete all ${savedVideos.length} saved video${savedVideos.length === 1 ? '' : 's'} and all of their clips from S3?`
    );
    if (!confirmed) {
      return;
    }

    setDeleteAllLoading(true);
    try {
      await deleteAllVideos();
      setSelectedClipIds([]);
      await refreshVideos();
    } catch (err) {
      setVideosError(err.message);
    } finally {
      setDeleteAllLoading(false);
    }
  }

  // Purpose: Validate the form, upload the video, and start a new processing job.
  // Input: event (SubmitEvent) from the upload form.
  // Output: Promise that resolves after the job is created and local state is updated.
  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setUploadProgress(0);

    if (hasActiveVideo) {
      return;
    }

    if (!file) {
      setError('Please select an .mp4, .mov, or .mkv file.');
      return;
    }
    if (!playerName.trim()) {
      setError('Please enter a player username.');
      return;
    }

    setLoading(true);
    try {
      setStatusText('Sending video to the local helper...');
      await startLocalJob(file, playerName.trim(), setUploadProgress);
      setStatusText('Job created. Local OCR and Lambda analysis are underway.');
      setFile(null);
      setResetToken((value) => value + 1);
      await refreshVideos();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const activeVideos = videos.filter((video) => video.status === 'queued' || video.status === 'processing');
  const savedVideos = videos.filter((video) => video.status !== 'queued' && video.status !== 'processing');
  const selectedClipCount = selectedClipIds.length;
  const totalSavedClipCount = savedVideos.reduce((sum, video) => sum + (video.clips?.length || 0), 0);

  return (
    <div className="dashboard-stack">
      <section className="upload-panel">
        <div className="section-header">
          <div>
            <h2>VOD Upload</h2>
          </div>
        </div>

        <UploadForm
          file={file}
          playerName={playerName}
          onFileChange={setFile}
          onPlayerNameChange={setPlayerName}
          onSubmit={handleSubmit}
          loading={loading}
          submitDisabled={hasActiveVideo || !playerName.trim()}
          submitDisabledMessage={
            hasActiveVideo
              ? 'Finish the current job before starting another upload.'
              : !playerName.trim()
              ? 'Enter a player username before starting the upload.'
              : ''
          }
          error={error}
          statusText={statusText}
          uploadProgress={uploadProgress}
          resetToken={resetToken}
        />
      </section>

      {activeVideos.length > 0 ? (
        <section className="video-section">
          <div className="section-header">
            <div>
              <h2>In Progress</h2>
              <p className="section-lead">These jobs are still working through OCR, Lambda analysis, and S3 upload.</p>
            </div>
          </div>

          <div className="video-stack">
            {activeVideos.map((video) => (
              <VideoJobCard
                key={video.videoId}
                video={video}
                selectedClipIds={selectedClipIds}
                onToggleClip={(clipId, checked) => updateClipSelection(clipId, checked)}
                onDiscardClip={(clipId) => handleDiscardClip(video.videoId, clipId)}
                discardingClipId={discardingClipId}
              />
            ))}
          </div>
        </section>
      ) : null}

      <section className="video-section">
        <div className="section-header">
          <div>
            <h2>Saved Videos</h2>
            <p className="section-lead">
              Finished videos stay here until you discard individual clips. Select any set of clips to pull down as a
              single merged video.
            </p>
          </div>
        </div>

        {videosLoading ? <p className="section-lead">Loading your clip library...</p> : null}
        {videosError ? <p className="error-text">{videosError}</p> : null}
        {!videosLoading && savedVideos.length === 0 ? (
          <p className="helper-text">No finished videos yet. Your completed jobs will stack here automatically.</p>
        ) : null}
        {savedVideos.length > 0 ? (
          <div className="video-toolbar">
            <p className="helper-text">
              {selectedClipCount > 0
                ? `${selectedClipCount} clip${selectedClipCount === 1 ? '' : 's'} selected across all saved videos.`
                : `${totalSavedClipCount} saved clip${totalSavedClipCount === 1 ? '' : 's'}.`}
            </p>
            <div className="clip-actions">
              <button
                type="button"
                className="primary-button"
                disabled={selectedClipCount === 0 || mergeLoading || deleteAllLoading}
                onClick={handleMergeSelected}
              >
                {mergeLoading
                  ? 'Preparing download...'
                  : selectedClipCount > 0
                  ? `Download ${selectedClipCount} Selected As One Video`
                  : 'Select Clips To Merge'}
              </button>
              <button
                type="button"
                className="danger-button"
                disabled={savedVideos.length === 0 || deleteAllLoading || mergeLoading || hasActiveVideo}
                onClick={handleDeleteAllVideos}
              >
                {deleteAllLoading ? 'Deleting All Videos...' : 'Delete All Videos'}
              </button>
            </div>
          </div>
        ) : null}

        <div className="video-stack">
          {savedVideos.map((video) => (
            <VideoJobCard
              key={video.videoId}
              video={video}
              selectedClipIds={selectedClipIds}
              onToggleClip={(clipId, checked) => updateClipSelection(clipId, checked)}
              onDiscardClip={(clipId) => handleDiscardClip(video.videoId, clipId)}
              discardingClipId={discardingClipId}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
