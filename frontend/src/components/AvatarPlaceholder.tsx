interface AvatarPlaceholderProps {
  signActions: string[]
}

export function AvatarPlaceholder({ signActions }: AvatarPlaceholderProps) {
  return (
    <aside className="avatar-panel" aria-labelledby="avatar-title">
      <div className="avatar-heading">
        <div>
          <span className="eyebrow">Sign support</span>
          <h2 id="avatar-title">Tutor Avatar</h2>
        </div>
        <span className="prototype-badge">Prototype</span>
      </div>

      <div
        className="avatar-stage"
        role="img"
        aria-label="Placeholder for the animated sign language tutor"
      >
        <div className="avatar-glow" />
        <div className="avatar-figure" aria-hidden="true">
          <div className="avatar-head" />
          <div className="avatar-body" />
          <div className="avatar-arm avatar-arm-left" />
          <div className="avatar-arm avatar-arm-right" />
          <div className="avatar-hand avatar-hand-left">L</div>
          <div className="avatar-hand avatar-hand-right">R</div>
        </div>
      </div>

      <div className="sign-status" aria-live="polite">
        <span>Signs for this step</span>
        <div className="sign-list">
          {signActions.map((sign, index) => (
            <span className="sign-chip" key={sign}>
              <span>{index + 1}</span>
              {sign.replaceAll('_', ' ')}
            </span>
          ))}
        </div>
      </div>

      <p className="avatar-note">
        The 3D sign animation will replace this placeholder after validation.
      </p>
    </aside>
  )
}
