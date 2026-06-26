import { useState } from 'react'
import { Card } from '../../components/Card'
import { FormField } from '../../components/FormField'
import { Button } from '../../components/Button'
import { useWizard } from '../../context/WizardContext'
import type { SessionMetadata } from '../../types/session'

export function SetupStep() {
  const { session, updateMetadata, importConfig, loading } = useWizard()
  const [importText, setImportText] = useState('')

  if (!session) {
    return <Card title="Setup">Starting session…</Card>
  }

  const metadata = session.metadata

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const next: SessionMetadata = {
      ...metadata,
      migration_id: String(form.get('migration_id')),
      client_id: String(form.get('client_id')),
      version: String(form.get('version')),
      source_count: Number(form.get('source_count')),
      target_count: Number(form.get('target_count')),
      base_path: String(form.get('base_path') || '') || null,
      target_path: String(form.get('target_path') || '') || null,
    }
    await updateMetadata(next)
  }

  const onImport = async () => {
    const config = JSON.parse(importText) as Record<string, unknown>
    await importConfig(config)
  }

  return (
    <>
      <Card title="Project setup">
        <p style={{ marginBottom: 16, color: 'var(--color-text-muted)' }}>
          Choose how many source and target files you need. Each target becomes one blueprint.
        </p>
        <form onSubmit={onSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <FormField label="Source files (N)">
              <input name="source_count" type="number" min={1} defaultValue={metadata.source_count} />
            </FormField>
            <FormField label="Target files (M)">
              <input name="target_count" type="number" min={1} defaultValue={metadata.target_count} />
            </FormField>
            <FormField label="migration_id">
              <input name="migration_id" defaultValue={metadata.migration_id} />
            </FormField>
            <FormField label="client_id">
              <input name="client_id" defaultValue={metadata.client_id} />
            </FormField>
            <FormField label="version">
              <input name="version" defaultValue={metadata.version} />
            </FormField>
          </div>
          <FormField label="base_path" hint="Optional — defaults to upload directory">
            <input name="base_path" defaultValue={metadata.base_path ?? ''} />
          </FormField>
          <FormField label="target_path" hint="Optional — defaults to upload directory/output">
            <input name="target_path" defaultValue={metadata.target_path ?? ''} />
          </FormField>
          <Button type="submit" variant="primary" disabled={loading}>
            Save setup
          </Button>
        </form>
      </Card>

      <Card title="Import existing config">
        <FormField label="config.json" hint="Paste JSON to load into the wizard">
          <textarea
            rows={8}
            value={importText}
            onChange={(event) => setImportText(event.target.value)}
            placeholder='{ "migration_id": "...", ... }'
          />
        </FormField>
        <Button type="button" variant="secondary" disabled={!importText || loading} onClick={onImport}>
          Import config
        </Button>
      </Card>
    </>
  )
}
