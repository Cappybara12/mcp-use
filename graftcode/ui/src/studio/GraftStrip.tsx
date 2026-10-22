import { useSyncExternalStore } from 'react'
import { graftActivity } from '../graft'

const fmt = (ms: number) => (ms < 1000 ? `${Math.max(1, Math.round(ms))} ms` : `${(ms / 1000).toFixed(1)} s`)
const name = (m: string) => m.replace(/^studio/, '').replace(/^./, c => c.toLowerCase())

/** A thin strip showing every call that goes through the Graft, so the Graftcode link is visible while you work. */
export function GraftStrip() {
  const calls = useSyncExternalStore(graftActivity.subscribe, graftActivity.snapshot)
  return (
    <div className="graft-strip" role="status" aria-label="Graft activity">
      <span className="graft-label"><i className="graft-dot" /> Graft</span>
      <div className="graft-calls">
        {calls.length === 0 && <span className="muted">Calls to the Python receiver appear here.</span>}
        {calls.slice(0, 10).map(c => (
          <span key={c.id} className={`graft-call ${c.ok ? '' : 'bad'}`}>{name(c.method)} <b>{fmt(c.ms)}</b></span>
        ))}
      </div>
    </div>
  )
}
