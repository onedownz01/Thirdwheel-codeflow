import { useFlowStore } from '../../store/flowStore';
import { useEffect } from 'react';

export function PlaybackScrubber() {
  const {
    traceComplete,
    traceEvents,
    playbackIndex,
    isPlaying,
    setPlaybackIndex,
    togglePlayback,
  } = useFlowStore();

  if (!traceComplete || traceEvents.length === 0) return null;

  const current = playbackIndex > 0 ? traceEvents[playbackIndex - 1] : null;

  useEffect(() => {
    if (!isPlaying) return;
    const id = window.setInterval(() => {
      const state = useFlowStore.getState();
      if (state.playbackIndex >= traceEvents.length) {
        state.togglePlayback();
        return;
      }
      state.setPlaybackIndex(state.playbackIndex + 1);
    }, 220);
    return () => window.clearInterval(id);
  }, [isPlaying, traceEvents.length]);

  return (
    <div className="scrubber">
      <div className="scrubber-top">
        <span>Reverse Playback</span>
        <span>
          {playbackIndex}/{traceEvents.length}
        </span>
      </div>
      <button className="secondary-btn" onClick={togglePlayback}>
        {isPlaying ? 'Pause' : 'Play'}
      </button>
      <input
        className="scrubber-input"
        type="range"
        min={0}
        max={traceEvents.length}
        value={playbackIndex}
        onChange={(e) => setPlaybackIndex(Number(e.target.value))}
      />
      {current && (
        <div className="scrubber-current">
          <span>{current.event_type}</span>
          <span>{current.fn_name}</span>
          <span>{current.timestamp_ms.toFixed(1)}ms</span>
        </div>
      )}
    </div>
  );
}
