import { useState } from 'react'
import './JobCard.css'

function scoreColor(score) {
  if (score >= 80) return { border: '#16a34a', text: '#15803d', bg: '#dcfce7' }
  if (score >= 60) return { border: '#ca8a04', text: '#a16207', bg: '#fef9c3' }
  return               { border: '#dc2626', text: '#b91c1c', bg: '#fee2e2' }
}

function statusStyle(status) {
  switch (status) {
    case 'To Apply':     return { bg: '#dbeafe', color: '#1d4ed8' }
    case 'Applied':      return { bg: '#dcfce7', color: '#15803d' }
    case 'Interviewing': return { bg: '#fef3c7', color: '#92400e' }
    default:             return { bg: '#f1f5f9', color: '#64748b' }
  }
}

function formatDate(str) {
  if (!str) return ''
  const datePart = str.slice(0, 10)
  const d = new Date(datePart + 'T00:00:00')
  if (isNaN(d)) return str
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function cleanSalary(s) {
  if (!s || s === 'Not disclosed' || s === 'N/A') return null
  return s
}

export default function JobCard({ job }) {
  const [expanded, setExpanded] = useState(false)
  const sc = scoreColor(job.matchScore)
  const st = statusStyle(job.status)
  const salary = cleanSalary(job.salary)

  return (
    <div
      className={`job-card ${expanded ? 'job-card--expanded' : ''}`}
      onClick={() => setExpanded(e => !e)}
    >
      <div className="card-main">
        {/* Score circle */}
        <div
          className="score-circle"
          style={{ borderColor: sc.border, color: sc.text, background: sc.bg }}
        >
          <span className="score-num">{job.matchScore}</span>
          <span className="score-pct">%</span>
        </div>

        {/* Info */}
        <div className="card-info">
          <div className="card-title-row">
            <h3 className="job-title">{job.title}</h3>
            <span
              className="status-badge"
              style={{ background: st.bg, color: st.color }}
            >
              {job.status}
            </span>
          </div>

          <p className="company-name">{job.company}</p>

          <div className="card-meta">
            {job.location && job.location !== 'N/A' && (
              <span className="meta-item">📍 {job.location}</span>
            )}
            {salary && (
              <span className="meta-item">💰 {salary}</span>
            )}
            {job.firstSeen && (
              <span className="meta-item">🗓 {formatDate(job.firstSeen)}</span>
            )}
          </div>
        </div>

        <span className="expand-arrow">{expanded ? '▲' : '▼'}</span>
      </div>

      {/* Expanded section */}
      {expanded && (
        <div className="card-expanded" onClick={e => e.stopPropagation()}>
          {job.matchReason && (
            <div className="match-reason">
              <p className="match-reason-label">Match reason</p>
              <p className="match-reason-text">{job.matchReason}</p>
            </div>
          )}

          <div className="card-actions">
            {job.applyUrl && job.applyUrl !== 'N/A' && (
              <a
                href={job.applyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-apply"
                onClick={e => e.stopPropagation()}
              >
                Apply Now →
              </a>
            )}
            {job.resumeLink && job.resumeLink !== 'N/A' &&
             !job.resumeLink.startsWith('See GitHub') && (
              <a
                href={job.resumeLink}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary"
                onClick={e => e.stopPropagation()}
              >
                Resume
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
