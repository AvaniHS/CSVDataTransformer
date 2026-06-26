import { useMemo, useState } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { FilterBuilder, type PredicateDraft } from '../../components/FilterBuilder'
import { FormField } from '../../components/FormField'
import { useWizard } from '../../context/WizardContext'
import type { BlueprintState, SourceFile } from '../../types/session'
import styles from './pre-filters.module.css'

function qualifiedColumns(alias: string, columns: string[]) {
  return columns.map((column) => `${alias}.${column}`)
}

const emptyDraft = (): PredicateDraft => ({
  left: '',
  operator: '==',
  right: '',
  right_type: 'literal',
})

function buildPredicate(draft: PredicateDraft): Record<string, unknown> {
  const predicate: Record<string, unknown> = {
    left: draft.left,
    operator: draft.operator,
  }
  if (draft.operator !== 'IS_NULL' && draft.operator !== 'IS_NOT_NULL') {
    predicate.right = draft.right
    predicate.right_type = draft.right_type ?? 'literal'
  }
  return predicate
}

function getFiltersForSource(blueprint: BlueprintState, sourceId: string): Record<string, unknown>[] {
  if (sourceId === blueprint.root_source_id) {
    return blueprint.pre_filters
  }
  const join = blueprint.joins.find((item) => item.source_id === sourceId)
  if (join) {
    return join.pre_filters
  }
  return blueprint.pending_join_pre_filters?.[sourceId] ?? []
}

function setFiltersForSource(
  blueprint: BlueprintState,
  sourceId: string,
  filters: Record<string, unknown>[],
): BlueprintState {
  if (sourceId === blueprint.root_source_id) {
    return { ...blueprint, pre_filters: filters }
  }
  const joinIndex = blueprint.joins.findIndex((item) => item.source_id === sourceId)
  if (joinIndex >= 0) {
    const joins = [...blueprint.joins]
    joins[joinIndex] = { ...joins[joinIndex], pre_filters: filters }
    return { ...blueprint, joins }
  }
  return {
    ...blueprint,
    pending_join_pre_filters: {
      ...(blueprint.pending_join_pre_filters ?? {}),
      [sourceId]: filters,
    },
  }
}

function migrateRootChange(blueprint: BlueprintState, newRootId: string): BlueprintState {
  const oldRootId = blueprint.root_source_id
  if (oldRootId === newRootId) return blueprint

  const pending = { ...(blueprint.pending_join_pre_filters ?? {}) }
  const oldRootFilters = blueprint.pre_filters
  const newRootFilters = pending[newRootId] ?? blueprint.joins.find((j) => j.source_id === newRootId)?.pre_filters ?? []

  // Move old root filters to pending for that source
  if (oldRootFilters.length) {
    pending[oldRootId] = oldRootFilters
  } else {
    delete pending[oldRootId]
  }

  // Pull new root filters from pending or join entry
  delete pending[newRootId]
  const joins = blueprint.joins
    .filter((join) => join.source_id !== newRootId)
    .map((join) => (join.source_id === oldRootId ? { ...join, pre_filters: oldRootFilters } : join))

  return {
    ...blueprint,
    root_source_id: newRootId,
    pre_filters: newRootFilters,
    pending_join_pre_filters: pending,
    joins,
  }
}

export function PreFiltersStep() {
  const { session, saveBlueprint } = useWizard()
  const [activeBlueprintIndex, setActiveBlueprintIndex] = useState(0)
  const [draftBySource, setDraftBySource] = useState<Record<string, PredicateDraft>>({})

  const blueprint = session?.blueprints[activeBlueprintIndex]

  const contextColumns = useMemo(() => {
    if (!session || !blueprint) return []
    const items: string[] = []
    for (const source of session.sources) {
      items.push(...qualifiedColumns(source.alias, source.columns.map((column) => column.name)))
    }
    return items
  }, [session, blueprint])

  if (!session || !blueprint) {
    return <Card title="Pre-filters">Configure setup and uploads first.</Card>
  }

  const draftFor = (sourceId: string) => draftBySource[sourceId] ?? emptyDraft()

  const setDraftFor = (sourceId: string, draft: PredicateDraft) => {
    setDraftBySource((current) => ({ ...current, [sourceId]: draft }))
  }

  const saveRoot = async (newRootId: string) => {
    await saveBlueprint(migrateRootChange(blueprint, newRootId))
  }

  const addFilter = async (sourceId: string) => {
    const draft = draftFor(sourceId)
    if (!draft.left) return
    const filters = [...getFiltersForSource(blueprint, sourceId), buildPredicate(draft)]
    await saveBlueprint(setFiltersForSource(blueprint, sourceId, filters))
    setDraftFor(sourceId, emptyDraft())
  }

  const removeFilter = async (sourceId: string, index: number) => {
    const filters = getFiltersForSource(blueprint, sourceId).filter((_, itemIndex) => itemIndex !== index)
    await saveBlueprint(setFiltersForSource(blueprint, sourceId, filters))
  }

  const renderSourcePanel = (source: SourceFile) => {
    const isRoot = source.source_id === blueprint.root_source_id
    const columns = qualifiedColumns(
      source.alias,
      source.columns.map((column) => column.name),
    )
    const filters = getFiltersForSource(blueprint, source.source_id)

    return (
      <div key={source.source_id} className={styles.sourcePanel}>
        <div className={styles.sourceHeader}>
          <div>
            <strong>{source.file_name}</strong>
            <span className={styles.alias}>
              alias: <code>{source.alias}</code>
            </span>
          </div>
          <span className={`${styles.badge} ${isRoot ? styles.badgeRoot : styles.badgeJoin}`}>
            {isRoot ? 'Root — filtered before joins' : 'Join source — filtered before merge'}
          </span>
        </div>
        <p className={styles.scopeHint}>
          Use columns from <code>{source.alias}.*</code> only. Each source is reduced independently before the join.
        </p>
        <FilterBuilder
          columns={columns}
          value={draftFor(source.source_id)}
          onChange={(value) => setDraftFor(source.source_id, value)}
        />
        <Button variant="primary" onClick={() => void addFilter(source.source_id)}>
          Add filter
        </Button>
        {filters.length ? (
          <ul className={styles.filterList}>
            {filters.map((filter, index) => (
              <li key={index}>
                <code>{JSON.stringify(filter)}</code>
                <Button type="button" variant="ghost" onClick={() => void removeFilter(source.source_id, index)}>
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.noFilters}>No filters — all rows from this file proceed to the join.</p>
        )}
      </div>
    )
  }

  return (
    <>
      {session.blueprints.length > 1 ? (
        <Card title="Blueprint">
          <select
            value={activeBlueprintIndex}
            onChange={(event) => setActiveBlueprintIndex(Number(event.target.value))}
          >
            {session.blueprints.map((item, index) => (
              <option key={item.blueprint_id} value={index}>
                {item.blueprint_id}
              </option>
            ))}
          </select>
        </Card>
      ) : null}

      <Card title="Pre-filter all sources before join">
        <p className={styles.hint}>
          Yes — every source can be pre-filtered before the join runs. The engine applies filters in this order:
        </p>
        <ol className={styles.pipeline}>
          <li>Filter the <strong>root</strong> table</li>
          <li>For each join file: read → filter → merge into the result</li>
        </ol>

        <FormField
          label="Root table"
          hint="Other sources are join tables. You can still pre-filter them here before step 4 wires the join."
        >
          <select value={blueprint.root_source_id} onChange={(event) => void saveRoot(event.target.value)}>
            {session.sources.map((source) => (
              <option key={source.source_id} value={source.source_id}>
                {source.file_name} ({source.alias})
              </option>
            ))}
          </select>
        </FormField>
      </Card>

      <Card title={`All sources (${session.sources.length})`}>
        {session.sources.map((source) => renderSourcePanel(source))}
      </Card>

      <div style={{ display: 'none' }}>{contextColumns.join(',')}</div>
    </>
  )
}

export function usePreFilterContext(session: ReturnType<typeof useWizard>['session'], blueprintIndex = 0) {
  const blueprint = session?.blueprints[blueprintIndex]
  return useMemo(() => {
    if (!session || !blueprint) return []
    const items: string[] = []
    for (const source of session.sources) {
      items.push(...qualifiedColumns(source.alias, source.columns.map((column) => column.name)))
    }
    for (const derivation of blueprint.derivations) {
      const name = derivation.variable_name
      if (typeof name === 'string') items.push(`deriv.${name}`)
    }
    return items
  }, [session, blueprint])
}
