import { useState } from 'react'
import { Button } from '../../components/Button'
import { FilterBuilder, type PredicateDraft } from '../../components/FilterBuilder'
import { ValidationBanner } from '../../components/ValidationBanner'
import {
  buildPredicate,
  emptyPredicate,
  formatCondition,
  hasMergeKey,
  isMergeKeyPredicate,
} from './joinConditionUtils'
import styles from './joins.module.css'

interface JoinConditionEditorProps {
  columns: string[]
  conditions: Record<string, unknown>[]
  onChange: (conditions: Record<string, unknown>[]) => void
}

export function JoinConditionEditor({ columns, conditions, onChange }: JoinConditionEditorProps) {
  const [draft, setDraft] = useState<PredicateDraft>(emptyPredicate)
  const [localError, setLocalError] = useState<string | null>(null)

  const addCondition = () => {
    setLocalError(null)
    const predicate = buildPredicate(draft)
    if (!predicate) {
      setLocalError('Complete all fields for this condition.')
      return
    }
    onChange([...conditions, predicate])
    setDraft(emptyPredicate())
  }

  const removeCondition = (index: number) => {
    onChange(conditions.filter((_, itemIndex) => itemIndex !== index))
  }

  const mergeKeyOk = hasMergeKey(conditions)

  return (
    <div className={styles.conditionEditor}>
      {localError ? <ValidationBanner tone="error" message={localError} /> : null}

      {!mergeKeyOk && conditions.length > 0 ? (
        <ValidationBanner
          tone="warning"
          message="Add at least one merge key: operator == with Value type = Column on both sides."
        />
      ) : null}

      {conditions.length ? (
        <ul className={styles.conditionList}>
          {conditions.map((condition, index) => (
            <li key={index}>
              <span>
                {isMergeKeyPredicate(condition) ? (
                  <span className={styles.mergeKeyBadge}>merge key</span>
                ) : (
                  <span className={styles.postMergeBadge}>post-merge</span>
                )}
                <code>{formatCondition(condition)}</code>
              </span>
              <Button type="button" variant="ghost" onClick={() => removeCondition(index)}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.emptyConditions}>No conditions yet — add a merge key first.</p>
      )}

      <FilterBuilder columns={columns} value={draft} onChange={setDraft} />
      <Button type="button" variant="secondary" onClick={addCondition}>
        Add condition
      </Button>
    </div>
  )
}
