import './StatsBar.css'

function StatCard({ label, value, accent }) {
  return (
    <div className={`stat-card ${accent ? 'stat-card--accent' : ''}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

export default function StatsBar({ stats }) {
  return (
    <div className="stats-bar">
      <div className="stats-inner">
        <StatCard label="Scraped today"   value={stats.scrapedToday} />
        <StatCard label="Matched today (60%+)" value={stats.matchedToday} accent />
        <StatCard label="Applied total"   value={stats.appliedTotal} />
      </div>
    </div>
  )
}
