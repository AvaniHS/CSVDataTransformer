import { useEffect, useState } from 'react'
import { generateConfig, validateConfig } from '../../api/session'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { ValidationBanner } from '../../components/ValidationBanner'
import { useWizard } from '../../context/WizardContext'

export function ReviewStep() {
  const { session, setNotice } = useWizard()
  const [configText, setConfigText] = useState('')
  const [validMessage, setValidMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!session) return
    setLoading(true)
    setError(null)
    generateConfig(session.session_id)
      .then((config) => {
        setConfigText(JSON.stringify(config, null, 2))
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [session])

  if (!session) {
    return <Card title="Review">Loading…</Card>
  }

  const onValidate = async () => {
    setLoading(true)
    setError(null)
    try {
      const config = JSON.parse(configText) as Record<string, unknown>
      const result = await validateConfig(config)
      setValidMessage(result.message)
      setNotice('Config passed G0 validation')
    } catch (err) {
      setValidMessage(null)
      setError(err instanceof Error ? err.message : 'Validation failed')
    } finally {
      setLoading(false)
    }
  }

  const onDownload = () => {
    const blob = new Blob([configText], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'config.json'
    anchor.click()
    URL.revokeObjectURL(url)
    setNotice('config.json downloaded')
  }

  return (
    <>
      {error ? <ValidationBanner tone="error" message={error} /> : null}
      {validMessage ? <ValidationBanner tone="success" message={validMessage} /> : null}

      <Card title="JSON preview">
        {loading && !configText ? <p>Generating config…</p> : null}
        <pre
          style={{
            background: '#f8f9fb',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            padding: 'var(--space-md)',
            overflow: 'auto',
            maxHeight: 480,
            fontSize: '0.85rem',
          }}
        >
          {configText || '{}'}
        </pre>
        <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
          <Button variant="primary" onClick={() => void onValidate()} disabled={loading || !configText}>
            Validate (G0)
          </Button>
          <Button variant="secondary" onClick={onDownload} disabled={!configText}>
            Download config.json
          </Button>
        </div>
      </Card>
    </>
  )
}
