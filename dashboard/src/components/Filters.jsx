import './Filters.css'

export default function Filters({
  search, onSearch,
  scoreFilter, onScoreFilter,
  statusFilter, onStatusFilter,
  dateFilter, onDateFilter,
  sortBy, onSortBy,
  hasFilters, onClear,
  totalShowing, totalJobs,
}) {
  return (
    <div className="filters">
      <div className="filters-row">
        <input
          className="filter-search"
          type="search"
          placeholder="Search title or company…"
          value={search}
          onChange={e => onSearch(e.target.value)}
        />

        <select
          className="filter-select"
          value={scoreFilter}
          onChange={e => onScoreFilter(e.target.value)}
        >
          <option value="all">All scores</option>
          <option value="80">80%+</option>
          <option value="70">70%+</option>
          <option value="60">60%+</option>
        </select>

        <select
          className="filter-select"
          value={statusFilter}
          onChange={e => onStatusFilter(e.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="To Apply">To Apply</option>
          <option value="Applied">Applied</option>
          <option value="Interviewing">Interviewing</option>
        </select>

        <select
          className="filter-select"
          value={dateFilter}
          onChange={e => onDateFilter(e.target.value)}
        >
          <option value="all">All dates</option>
          <option value="today">Today</option>
          <option value="3days">Last 3 days</option>
          <option value="week">This week</option>
        </select>

        <select
          className="filter-select"
          value={sortBy}
          onChange={e => onSortBy(e.target.value)}
        >
          <option value="score">Sort: Score ↓</option>
          <option value="date">Sort: Newest first</option>
        </select>

        {hasFilters && (
          <button className="btn-clear" onClick={onClear}>
            Clear
          </button>
        )}
      </div>

      <div className="filters-meta">
        Showing <strong>{totalShowing}</strong> of <strong>{totalJobs}</strong> jobs
      </div>
    </div>
  )
}
