import { useState, useEffect, useMemo } from 'react'
import { useSheetData } from './hooks/useSheetData'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import Filters from './components/Filters'
import JobCard from './components/JobCard'
import './App.css'

function parseDatePrefix(str) {
  if (!str) return null
  const d = new Date(str.slice(0, 10) + 'T00:00:00')
  return isNaN(d) ? null : d
}

function isToday(str) {
  const d = parseDatePrefix(str)
  if (!d) return false
  const today = new Date()
  return d.toDateString() === today.toDateString()
}

function isWithinDays(str, days) {
  const d = parseDatePrefix(str)
  if (!d) return false
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  return d >= cutoff
}

export default function App() {
  const { jobs, loading, error, lastFetched, fetchData } = useSheetData()

  const [search,       setSearch]       = useState('')
  const [scoreFilter,  setScoreFilter]  = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [dateFilter,   setDateFilter]   = useState('all')
  const [sortBy,       setSortBy]       = useState('score')

  useEffect(() => { fetchData() }, [fetchData])

  const filtered = useMemo(() => {
    let result = [...jobs]

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        j => j.title.toLowerCase().includes(q) || j.company.toLowerCase().includes(q)
      )
    }

    if (scoreFilter !== 'all') {
      const min = parseInt(scoreFilter, 10)
      result = result.filter(j => j.matchScore >= min)
    }

    if (statusFilter !== 'all') {
      result = result.filter(j => j.status === statusFilter)
    }

    if (dateFilter === 'today') {
      result = result.filter(j => isToday(j.firstSeen))
    } else if (dateFilter === '3days') {
      result = result.filter(j => isWithinDays(j.firstSeen, 3))
    } else if (dateFilter === 'week') {
      result = result.filter(j => isWithinDays(j.firstSeen, 7))
    }

    result.sort((a, b) =>
      sortBy === 'score'
        ? b.matchScore - a.matchScore
        : (parseDatePrefix(b.firstSeen) || 0) - (parseDatePrefix(a.firstSeen) || 0)
    )

    return result
  }, [jobs, search, scoreFilter, statusFilter, dateFilter, sortBy])

  const stats = useMemo(() => ({
    scrapedToday:  jobs.filter(j => isToday(j.firstSeen)).length,
    matchedToday:  jobs.filter(j => isToday(j.firstSeen) && j.matchScore >= 60).length,
    appliedTotal:  jobs.filter(j => j.status === 'Applied').length,
  }), [jobs])

  const lastUpdated = useMemo(() =>
    jobs.reduce((latest, j) => (j.lastUpdated > latest ? j.lastUpdated : latest), ''),
    [jobs]
  )

  const toApplyCount = useMemo(
    () => jobs.filter(j => j.status === 'To Apply').length,
    [jobs]
  )

  const hasFilters =
    search || scoreFilter !== 'all' || statusFilter !== 'all' || dateFilter !== 'all'

  function clearFilters() {
    setSearch('')
    setScoreFilter('all')
    setStatusFilter('all')
    setDateFilter('all')
  }

  return (
    <div className="app">
      <Header
        totalJobs={jobs.length}
        toApplyCount={toApplyCount}
        lastUpdated={lastUpdated}
        onRefresh={fetchData}
        loading={loading}
      />
      <StatsBar stats={stats} />

      <main className="main">
        <Filters
          search={search}             onSearch={setSearch}
          scoreFilter={scoreFilter}   onScoreFilter={setScoreFilter}
          statusFilter={statusFilter} onStatusFilter={setStatusFilter}
          dateFilter={dateFilter}     onDateFilter={setDateFilter}
          sortBy={sortBy}             onSortBy={setSortBy}
          hasFilters={hasFilters}     onClear={clearFilters}
          totalShowing={filtered.length}
          totalJobs={jobs.length}
        />

        {loading && (
          <div className="state-center">
            <div className="spinner" />
            <p>Loading jobs…</p>
          </div>
        )}

        {!loading && error && (
          <div className="state-center error">
            <p>⚠ Error loading data: {error}</p>
            <button onClick={fetchData}>Retry</button>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="state-center">
            <p>No jobs found{hasFilters ? ' matching current filters' : ''}.</p>
            {hasFilters && (
              <button onClick={clearFilters}>Clear filters</button>
            )}
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="job-grid">
            {filtered.map((job, i) => (
              <JobCard key={`${job.company}-${job.title}-${i}`} job={job} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
