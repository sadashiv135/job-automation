import { useState, useCallback } from 'react'

const SHEET_ID = '1nLEiNeV9EznLNrVgodXvfD6w7ZCSa2Gpm2x9QrFpdW0'
const API_KEY  = import.meta.env.VITE_SHEETS_API_KEY

// Apply URL is stored as =HYPERLINK("url", "Apply Here") — extract the URL
function extractUrl(cell) {
  if (!cell) return ''
  const m = String(cell).match(/=HYPERLINK\("([^"]+)"/)
  return m ? m[1] : String(cell)
}

function parseRow(row) {
  return {
    firstSeen:       row[0]  || '',
    lastUpdated:     row[1]  || '',
    title:           row[2]  || '',
    company:         row[3]  || '',
    location:        row[4]  || '',
    experienceLevel: row[5]  || '',
    visaFilter:      row[6]  || '',
    salary:          row[7]  || '',
    matchScore:      parseInt(row[8], 10) || 0,
    applyUrl:        extractUrl(row[9]),
    resumeLink:      row[10] || '',
    coverLetterLink: row[11] || '',
    status:          row[12] || '',
    matchReason:     row[13] || '',
  }
}

export function useSheetData() {
  const [jobs, setJobs]           = useState([])
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [lastFetched, setLastFetched] = useState(null)

  const fetchData = useCallback(async () => {
    if (!API_KEY || API_KEY === 'your_google_sheets_api_key_here') {
      setError('VITE_SHEETS_API_KEY is not set. Add it to dashboard/.env')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const url =
        `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}` +
        `/values/Sheet1!A:N?key=${API_KEY}&valueRenderOption=FORMULA`
      const res = await fetch(url)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error?.message || `HTTP ${res.status}`)
      }
      const data = await res.json()
      const rows = data.values || []
      // row[0] is the header row — skip it; also skip rows with no title
      const parsed = rows.slice(1).filter(r => r[2]).map(parseRow)
      setJobs(parsed)
      setLastFetched(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { jobs, loading, error, lastFetched, fetchData }
}
