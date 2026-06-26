import type { PredicateDraft } from '../../components/FilterBuilder'

export function emptyPredicate(): PredicateDraft {
  return { left: '', operator: '==', right: '', right_type: 'column' }
}

export function buildPredicate(draft: PredicateDraft): Record<string, unknown> | null {
  if (!draft.left || !draft.operator) return null
  const nullOperator = draft.operator === 'IS_NULL' || draft.operator === 'IS_NOT_NULL'
  const predicate: Record<string, unknown> = {
    left: draft.left,
    operator: draft.operator,
  }
  if (!nullOperator) {
    if (draft.right === undefined || draft.right === '') return null
    predicate.right = draft.right
    predicate.right_type = draft.right_type ?? 'literal'
  }
  return predicate
}

/** Engine requires at least one == column-to-column pair for pandas merge keys. */
export function hasMergeKey(conditions: Record<string, unknown>[]): boolean {
  return conditions.some(
    (condition) =>
      condition.operator === '==' &&
      condition.right_type === 'column' &&
      typeof condition.left === 'string' &&
      typeof condition.right === 'string' &&
      condition.left.length > 0 &&
      condition.right.length > 0,
  )
}

export function isMergeKeyPredicate(condition: Record<string, unknown>): boolean {
  return (
    condition.operator === '==' &&
    condition.right_type === 'column' &&
    typeof condition.left === 'string' &&
    typeof condition.right === 'string'
  )
}

export function formatCondition(condition: Record<string, unknown>): string {
  const left = String(condition.left ?? '')
  const op = String(condition.operator ?? '')
  if (op === 'IS_NULL' || op === 'IS_NOT_NULL') {
    return `${left} ${op}`
  }
  const right = condition.right_type === 'column' ? String(condition.right) : JSON.stringify(condition.right)
  return `${left} ${op} ${right}`
}
