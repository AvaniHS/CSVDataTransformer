import { useState } from 'react'
import { uploadSource, uploadTarget, updateSourceAlias } from '../../api/session'
import { Card } from '../../components/Card'
import { FormField } from '../../components/FormField'
import { SchemaTable } from '../../components/SchemaTable'
import { ValidationBanner } from '../../components/ValidationBanner'
import { useWizard } from '../../context/WizardContext'

export function UploadStep() {
  const { session, refreshSession, setNotice, loading } = useWizard()
  const [localError, setLocalError] = useState<string | null>(null)
  const [targetWarning, setTargetWarning] = useState<string | null>(null)

  if (!session) return <Card title="Upload">Loading session…</Card>

  const { metadata, sources, targets } = session

  const handleSource = async (file: File) => {
    setLocalError(null)
    await uploadSource(session.session_id, file)
    await refreshSession()
    setNotice(`Uploaded source ${file.name}`)
  }

  const handleTarget = async (file: File) => {
    setLocalError(null)
    setTargetWarning(null)
    try {
      const result = await uploadTarget(session.session_id, file)
      await refreshSession()
      if (result.warning) {
        setTargetWarning(result.warning)
      } else {
        setNotice(`Uploaded target ${file.name}`)
      }
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Target upload failed')
    }
  }

  const updateAlias = async (sourceId: string, alias: string) => {
    await updateSourceAlias(session.session_id, sourceId, alias)
    await refreshSession()
  }

  const sourcesComplete = sources.length >= metadata.source_count
  const targetsComplete = targets.length >= metadata.target_count

  return (
    <>
      {localError ? <ValidationBanner tone="error" message={localError} /> : null}
      {targetWarning ? <ValidationBanner tone="warning" message={targetWarning} /> : null}

      <Card title={`Source files (${sources.length}/${metadata.source_count})`}>
        <FormField label="Upload source CSV" hint="Must include header row and at least one data row">
          <input
            type="file"
            accept=".csv,text/csv"
            disabled={loading || sources.length >= metadata.source_count}
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void handleSource(file)
              event.currentTarget.value = ''
            }}
          />
        </FormField>

        {sources.map((source) => (
          <div key={source.source_id} style={{ marginTop: 16 }}>
            <FormField label={`Alias for ${source.file_name}`}>
              <input
                defaultValue={source.alias}
                onBlur={(event) => void updateAlias(source.source_id, event.target.value)}
              />
            </FormField>
            <SchemaTable
              columns={source.columns.map((column) => column.name)}
              rows={source.sample_rows}
            />
          </div>
        ))}
      </Card>

      <Card title={`Target files (${targets.length}/${metadata.target_count})`}>
        <FormField
          label="Upload target CSV"
          hint="Header row defines output columns. Extra data rows are removed automatically."
        >
          <input
            type="file"
            accept=".csv,text/csv"
            disabled={loading || targets.length >= metadata.target_count}
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void handleTarget(file)
              event.currentTarget.value = ''
            }}
          />
        </FormField>

        {targets.map((target) => (
          <div key={target.target_id} style={{ marginTop: 16 }}>
            <p>
              <strong>{target.file_name}</strong> — {target.headers.join(', ')}
            </p>
          </div>
        ))}
      </Card>

      {!sourcesComplete || !targetsComplete ? (
        <ValidationBanner
          tone="warning"
          message="Upload all required source and target files before continuing."
        />
      ) : null}
    </>
  )
}
