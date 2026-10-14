interface BalanceScaleProps {
  variableLabel: string
  leftSign: '+' | '-'
  leftConstant: number
  rightValue: number
  solved: boolean
  wobbling: boolean
}

// Purely visual: a seesaw with the equation's two sides on each pan. It
// always renders level (the equation is always true) — wobbling briefly
// signals a wrong move, and "solved" drops the constant off the left pan
// while the right pan's number falls to match, showing the same operation
// applied to both sides at once.
export function BalanceScale({
  variableLabel,
  leftSign,
  leftConstant,
  rightValue,
  solved,
  wobbling,
}: BalanceScaleProps) {
  return (
    <div
      className={`balance-scale ${wobbling ? 'wobbling' : ''}`}
      role="img"
      aria-label={
        solved
          ? `Balance showing ${variableLabel} equals ${rightValue}`
          : `Balance showing ${variableLabel} ${leftSign} ${leftConstant} equals ${rightValue}`
      }
    >
      <div className="balance-beam">
        <div className="balance-pan left">
          <span className="balance-chip variable">{variableLabel}</span>
          {!solved && (
            <span className="balance-chip constant">
              {leftSign} {leftConstant}
            </span>
          )}
        </div>
        <div className="balance-pan right">
          <span className="balance-chip constant">{rightValue}</span>
        </div>
      </div>
      <div className="balance-fulcrum" aria-hidden="true" />
    </div>
  )
}
