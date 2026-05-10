import './Header.css'

function formatTimestamp(str) {
  if (!str) return '—'
  // "2026-05-10 14:30 CDT" → "May 10, 2:30 PM CDT"
  const datePart = str.slice(0, 10)
  const d = new Date(datePart + 'T00:00:00')
  if (isNaN(d)) return str
  const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const time = str.slice(11, 16) // "14:30"
  const tz   = str.slice(17)     // "CDT"
  if (!time) return date
  const [h, m] = time.split(':').map(Number)
  const ampm = h >= 12 ? 'PM' : 'AM'
  const h12  = ((h % 12) || 12)
  return `${date}, ${h12}:${String(m).padStart(2, '0')} ${ampm}${tz ? ' ' + tz : ''}`
}

export default function Header({ totalJobs, toApplyCount, lastUpdated, onRefresh, loading }) {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-left">
          <h1 className="header-title">Job Tracker</h1>
          <div className="header-chips">
            <span className="chip chip-total">{totalJobs} total</span>
            <span className="chip chip-apply">{toApplyCount} to apply</span>
          </div>
        </div>
        <div className="header-right">
          {lastUpdated && (
            <span className="header-updated">
              Updated {formatTimestamp(lastUpdated)}
            </span>
          )}
          <button
            className={`btn-refresh ${loading ? 'loading' : ''}`}
            onClick={onRefresh}
            disabled={loading}
            title="Refresh jobs"
          >
            {loading ? '...' : '↺ Refresh'}
          </button>
        </div>
      </div>
    </header>
  )
}
