import { useState } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { FilterBuilder, type PredicateDraft } from '../../components/FilterBuilder'
import { useWizard } from '../../context/WizardContext'
import type { BlueprintState } from '../../types/session'

export function PostFiltersStep() {
  const { session, saveBlueprint } = useWizard()
  const [blueprintIndex, setBlueprintIndex] = useState(0)
  const [draft, setDraft] = useState<PredicateDraft>({
    left: '',
    operator: '==',
    right: '',
    right_type: 'literal',
  })

  const blueprint = session?.blueprints[blueprintIndex]
  const target = session?.targets.find((item) => item.target_id === blueprint?.target_id)

  if (!session || !blueprint || !target) {
    return <Card title="Post-filters">Upload targets first.</Card>
  }

  const addFilter = async () => {
    if (!draft.left) return
    const predicate: Record<string, unknown> = {
      left: draft.left,
      operator: draft.operator,
    }
    if (draft.operator !== 'IS_NULL' && draft.operator !== 'IS_NOT_NULL') {
      predicate.right = draft.right
      predicate.right_type = draft.right_type ?? 'literal'
    }
    const next: BlueprintState = {
      ...blueprint,
      post_filters: [...blueprint.post_filters, predicate],
    }
    await saveBlueprint(next)
    setDraft({ left: '', operator: '==', right: '', right_type: 'literal' })
  }

  return (
    <>
      {session.blueprints.length > 1 ? (
        <Card title="Blueprint">
          <select value={blueprintIndex} onChange={(event) => setBlueprintIndex(Number(event.target.value))}>
            {session.blueprints.map((item, index) => (
              <option key={item.blueprint_id} value={index}>
                {item.blueprint_id}
              </option>
            ))}
          </select>
        </Card>
      ) : null}

      <Card title="Post-filters on target columns">
        <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>
          Rules reference target column names from your empty CSV headers.
        </p>
        <FilterBuilder columns={target.headers} value={draft} onChange={setDraft} />
        <Button variant="primary" onClick={() => void addFilter()}>
          Add post-filter
        </Button>
        <ul style={{ marginTop: 16 }}>
          {blueprint.post_filters.map((filter, index) => (
            <li key={index}>
              <code>{JSON.stringify(filter)}</code>
            </li>
          ))}
        </ul>
      </Card>
    </>
  )
}
