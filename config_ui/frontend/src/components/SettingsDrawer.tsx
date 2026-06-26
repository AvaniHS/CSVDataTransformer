import { useState } from 'react'
import { Button } from './Button'
import { FormField } from './FormField'
import { useWizard } from '../context/WizardContext'
import styles from './settings.module.css'

export function SettingsDrawer() {
  const { session, updateMetadata, loading } = useWizard()
  const [open, setOpen] = useState(false)
  const metadata = session?.metadata

  if (!metadata) return null

  const save = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    await updateMetadata({
      ...metadata,
      migration_id: String(form.get('migration_id') ?? metadata.migration_id),
      client_id: String(form.get('client_id') ?? metadata.client_id),
      version: String(form.get('version') ?? metadata.version),
      base_path: String(form.get('base_path') ?? '') || null,
      target_path: String(form.get('target_path') ?? '') || null,
    })
    setOpen(false)
  }

  return (
    <div className={styles.wrap}>
      <Button type="button" onClick={() => setOpen((value) => !value)} aria-label="Toggle metadata settings">
        Metadata ▾
      </Button>
      {open ? (
        <form className={styles.drawer} onSubmit={save}>
          <FormField label="migration_id">
            <input name="migration_id" defaultValue={metadata.migration_id} />
          </FormField>
          <FormField label="client_id">
            <input name="client_id" defaultValue={metadata.client_id} />
          </FormField>
          <FormField label="version">
            <input name="version" defaultValue={metadata.version} />
          </FormField>
          <FormField label="base_path" hint="Defaults to upload directory when empty">
            <input name="base_path" defaultValue={metadata.base_path ?? ''} />
          </FormField>
          <FormField label="target_path" hint="Defaults to upload directory/output when empty">
            <input name="target_path" defaultValue={metadata.target_path ?? ''} />
          </FormField>
          <Button type="submit" variant="primary" disabled={loading}>
            Save metadata
          </Button>
        </form>
      ) : null}
    </div>
  )
}
