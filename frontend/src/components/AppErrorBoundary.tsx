import React from 'react';

interface State {
  hasError: boolean;
  message: string;
}

export class AppErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  constructor(props: React.PropsWithChildren) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : String(error),
    };
  }

  componentDidCatch(error: unknown) {
    // Keep stack in console for debugging while preserving UI.
    // eslint-disable-next-line no-console
    console.error('App runtime error:', error);
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="runtime-fallback">
        <div className="runtime-fallback-card">
          <div className="runtime-fallback-title">Runtime UI error</div>
          <div className="runtime-fallback-body">{this.state.message}</div>
          <button className="primary-btn" onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      </div>
    );
  }
}
