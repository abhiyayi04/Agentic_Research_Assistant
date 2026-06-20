import { useState } from 'react'

const API_BASE = 'http://localhost:8000'

const styles = {
  container: {
    marginBottom: '1.5rem',
    padding: '1rem 1.25rem',
    border: '1px dashed #d1d5db',
    borderRadius: '8px',
    background: '#fafafa',
  },
  label: {
    display: 'block',
    marginBottom: '0.6rem',
    fontWeight: 600,
    fontSize: '0.875rem',
    color: '#374151',
  },
  row: { display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' },
  fileBtn: {
    cursor: 'pointer',
    padding: '0.4rem 0.75rem',
    background: '#f3f4f6',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    fontSize: '0.85rem',
    color: '#374151',
    whiteSpace: 'nowrap',
  },
  uploadBtn: (disabled) => ({
    padding: '0.4rem 1rem',
    background: disabled ? '#93c5fd' : '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.85rem',
    cursor: disabled ? 'not-allowed' : 'pointer',
  }),
  success: { fontSize: '0.85rem', color: '#059669' },
  error: { fontSize: '0.85rem', color: '#dc2626' },
}

export default function FileUpload() {
  const [file, setFile] = useState(null)
  // status: null | 'uploading' | { chunk_count, filename } | 'error'
  const [status, setStatus] = useState(null)

  const handleFileChange = (e) => {
    setFile(e.target.files[0] || null)
    setStatus(null)
  }

  const upload = async () => {
    if (!file) return
    setStatus('uploading')
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: form })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setStatus(data)
      setFile(null)
    } catch {
      setStatus('error')
    }
  }

  const isUploading = status === 'uploading'
  const isSuccess = status && status !== 'uploading' && status !== 'error'

  return (
    <div style={styles.container}>
      <span style={styles.label}>Upload Document</span>
      <div style={styles.row}>
        <label style={styles.fileBtn}>
          {file ? file.name : 'Choose PDF or TXT'}
          <input
            type="file"
            accept=".pdf,.txt"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
        </label>
        <button
          onClick={upload}
          disabled={!file || isUploading}
          style={styles.uploadBtn(!file || isUploading)}
        >
          {isUploading ? 'Uploading...' : 'Upload'}
        </button>
        {isSuccess && (
          <span style={styles.success}>
            Indexed {status.chunk_count} chunks from {status.filename}
          </span>
        )}
        {status === 'error' && (
          <span style={styles.error}>Upload failed — check file format or server logs</span>
        )}
      </div>
    </div>
  )
}
