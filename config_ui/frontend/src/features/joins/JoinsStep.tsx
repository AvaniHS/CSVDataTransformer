import { useMemo, useState } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { FormField } from '../../components/FormField'
import { ValidationBanner } from '../../components/ValidationBanner'
import { useWizard } from '../../context/WizardContext'
import { JOIN_TYPES, type BlueprintState, type JoinState } from '../../types/session'
import { JoinConditionEditor } from './JoinConditionEditor'
import { hasMergeKey } from './joinConditionUtils'
import styles from './joins.module.css'

function qualifiedColumns(alias: string, columns: string[]) {
  return columns.map((column) => `${alias}.${column}`)
}

export function JoinsStep() {
  const { session, saveBlueprint, setNotice } = useWizard()
  const [blueprintIndex, setBlueprintIndex] = useState(0)
  const [joinSourceId, setJoinSourceId] = useState('')
  const [joinType, setJoinType] = useState<JoinState['join_type']>('LEFT')
  const [draftConditions, setDraftConditions] = useState<Record<string, unknown>[]>([])
  const [formError, setFormError] = useState<string | null>(null)

  const blueprint = session?.blueprints[blueprintIndex]

  const allColumns = useMemo(() => {
    if (!session) return []
    return session.sources.flatMap((source) =>
      qualifiedColumns(source.alias, source.columns.map((column) => column.name)),
    )
  }, [session])

  if (!session || !blueprint) {
    return <Card title="Joins">Upload sources first.</Card>
  }

  const root = session.sources.find((source) => source.source_id === blueprint.root_source_id)
  const otherSources = session.sources.filter((source) => source.source_id !== blueprint.root_source_id)
  const usedJoinSourceIds = new Set(blueprint.joins.map((join) => join.source_id))
  const availableJoinSources = otherSources.filter((source) => !usedJoinSourceIds.has(source.source_id))

  const saveRoot = async (rootSourceId: string) => {
    const next: BlueprintState = { ...blueprint, root_source_id: rootSourceId, joins: [] }
    await saveBlueprint(next)
  }

  const addJoin = async () => {
    setFormError(null)
    if (!joinSourceId) {
      setFormError('Select a join source.')
      return
    }
    if (!hasMergeKey(draftConditions)) {
      setFormError('Add at least one merge key condition (== with Column on both sides).')
      return
    }

    const pending = blueprint.pending_join_pre_filters?.[joinSourceId] ?? []
    const join: JoinState = {
      source_id: joinSourceId,
      join_type: joinType,
      conditions: draftConditions,
      pre_filters: pending,
    }
    const nextPending = { ...(blueprint.pending_join_pre_filters ?? {}) }
    delete nextPending[joinSourceId]
    const next: BlueprintState = {
      ...blueprint,
      joins: [...blueprint.joins, join],
      pending_join_pre_filters: nextPending,
    }
    await saveBlueprint(next)
    setJoinSourceId('')
    setJoinType('LEFT')
    setDraftConditions([])
    setNotice('Join added')
  }

  const updateJoinConditions = async (joinIndex: number, conditions: Record<string, unknown>[]) => {
    if (!hasMergeKey(conditions)) {
      setFormError('Each join must keep at least one merge key (== with Column on both sides).')
      return
    }
    setFormError(null)
    const joins = [...blueprint.joins]
    joins[joinIndex] = { ...joins[joinIndex], conditions }
    await saveBlueprint({ ...blueprint, joins })
  }

  const removeJoin = async (joinIndex: number) => {
    const joins = blueprint.joins.filter((_, index) => index !== joinIndex)
    await saveBlueprint({ ...blueprint, joins })
  }

  const updateJoinType = async (joinIndex: number, type: JoinState['join_type']) => {
    const joins = [...blueprint.joins]
    joins[joinIndex] = { ...joins[joinIndex], join_type: type }
    await saveBlueprint({ ...blueprint, joins })
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

      <Card title="Join rules">
        <p className={styles.hint}>
          Each join needs at least one <strong>merge key</strong> (<code>==</code> between two columns). You can add
          extra conditions (literals, other operators) applied after the merge.
        </p>
        <ul className={styles.limitations}>
          <li>
            <strong>Not supported:</strong> join on <code>deriv.*</code> — derivations run after joins.
          </li>
          <li>
            <strong>Not supported:</strong> expression-form join keys — use source columns or add keys to your CSVs.
          </li>
          <li>Pre-filters per source are configured in the Pre-filters step.</li>
        </ul>
      </Card>

      <Card title="Root source">
        <FormField label="Root table" hint="Change root in Pre-filters step to keep pre-filter alignment.">
          <select value={blueprint.root_source_id} onChange={(event) => void saveRoot(event.target.value)}>
            {session.sources.map((source) => (
              <option key={source.source_id} value={source.source_id}>
                {source.file_name} ({source.alias})
              </option>
            ))}
          </select>
        </FormField>
        {root ? (
          <p className={styles.hint}>
            Root alias: <code>{root.alias}</code>
          </p>
        ) : null}
      </Card>

      {otherSources.length ? (
        <Card title="Add join">
          {formError ? <ValidationBanner tone="error" message={formError} /> : null}

          <FormField label="Join source">
            <select value={joinSourceId} onChange={(event) => setJoinSourceId(event.target.value)}>
              <option value="">Select source</option>
              {availableJoinSources.map((source) => (
                <option key={source.source_id} value={source.source_id}>
                  {source.file_name} ({source.alias})
                </option>
              ))}
            </select>
          </FormField>

          {availableJoinSources.length === 0 && otherSources.length > 0 ? (
            <ValidationBanner tone="warning" message="All other sources are already joined in this blueprint." />
          ) : null}

          <FormField label="Join type">
            <select value={joinType} onChange={(event) => setJoinType(event.target.value as JoinState['join_type'])}>
              {JOIN_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </FormField>

          <JoinConditionEditor
            columns={allColumns}
            conditions={draftConditions}
            onChange={setDraftConditions}
          />

          <div className={styles.joinActions}>
            <Button variant="primary" onClick={() => void addJoin()} disabled={!joinSourceId}>
              Add join
            </Button>
          </div>
        </Card>
      ) : (
        <Card title="Joins">
          <p className={styles.hint}>Single-source blueprint — joins not required.</p>
        </Card>
      )}

      {blueprint.joins.map((join, index) => {
        const source = session.sources.find((item) => item.source_id === join.source_id)
        return (
          <Card key={`${join.source_id}-${index}`} title={`Join ${index + 1}: ${source?.file_name ?? join.source_id}`}>
            <FormField label="Join type">
              <select
                value={join.join_type}
                onChange={(event) => void updateJoinType(index, event.target.value as JoinState['join_type'])}
              >
                {JOIN_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </FormField>

            <JoinConditionEditor
              columns={allColumns}
              conditions={join.conditions}
              onChange={(conditions) => void updateJoinConditions(index, conditions)}
            />

            {join.pre_filters.length ? (
              <p className={styles.hint}>
                Pre-filters: {join.pre_filters.length} (edit in Pre-filters step)
              </p>
            ) : null}

            <div className={styles.joinActions}>
              <Button type="button" variant="ghost" onClick={() => void removeJoin(index)}>
                Remove join
              </Button>
            </div>
          </Card>
        )
      })}
    </>
  )
}

export function useJoinContext(session: ReturnType<typeof useWizard>['session']) {
  return useMemo(() => {
    if (!session) return []
    return session.sources.flatMap((source) =>
      qualifiedColumns(source.alias, source.columns.map((column) => column.name)),
    )
  }, [session])
}
