import { useMemo, useState } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { FormField } from '../../components/FormField'
import { useWizard } from '../../context/WizardContext'
import { CAST_TYPES, SOURCE_TYPES, type BlueprintState, type MappingState } from '../../types/session'

export function MappingsStep() {
  const { session, saveBlueprint } = useWizard()
  const [blueprintIndex, setBlueprintIndex] = useState(0)

  const blueprint = session?.blueprints[blueprintIndex]
  const target = session?.targets.find((item) => item.target_id === blueprint?.target_id)

  const sourceColumns = useMemo(() => {
    if (!session) return []
    return session.sources.flatMap((source) =>
      source.columns.map((column) => ({
        label: `${source.alias}.${column.name}`,
        value: `${source.alias}.${column.name}`,
        cast: column.inferred_cast,
      })),
    )
  }, [session])

  const derivColumns = useMemo(() => {
    if (!blueprint) return []
    return blueprint.derivations
      .map((item) => (typeof item.variable_name === 'string' ? `deriv.${item.variable_name}` : null))
      .filter((item): item is string => Boolean(item))
  }, [blueprint])

  if (!session || !blueprint || !target) {
    return <Card title="Mappings">Upload targets first.</Card>
  }

  const ensureMappings = (): MappingState[] => {
    if (blueprint.mappings.length) return blueprint.mappings
    return target.headers.map((header) => {
      const match = sourceColumns.find((column) => column.label.endsWith(`.${header}`))
      return {
        target_column: header,
        source_type: match ? 'DIRECT' : 'EXPRESSION',
        source_value: match?.value ?? header,
        cast_to: match?.cast ?? 'str',
        is_nullable: true,
      }
    })
  }

  const mappings = ensureMappings()

  const updateMapping = async (index: number, patch: Partial<MappingState>) => {
    const nextMappings = mappings.map((mapping, mappingIndex) =>
      mappingIndex === index ? { ...mapping, ...patch } : mapping,
    )
    const next: BlueprintState = { ...blueprint, mappings: nextMappings }
    await saveBlueprint(next)
  }

  const initializeMappings = async () => {
    await saveBlueprint({ ...blueprint, mappings })
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

      <Card title={`Mappings for ${target.file_name}`}>
        {!blueprint.mappings.length ? (
          <Button variant="primary" onClick={() => void initializeMappings()}>
            Generate mapping rows from headers
          </Button>
        ) : null}

        {mappings.map((mapping, index) => (
          <div
            key={mapping.target_column}
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              gap: 12,
              marginTop: 16,
              paddingTop: 16,
              borderTop: '1px solid var(--color-border)',
            }}
          >
            <FormField label="Target column">
              <input value={mapping.target_column} readOnly />
            </FormField>
            <FormField label="Source type">
              <select
                value={mapping.source_type}
                onChange={(event) =>
                  void updateMapping(index, { source_type: event.target.value as MappingState['source_type'] })
                }
              >
                {SOURCE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Source value">
              {mapping.source_type === 'DIRECT' ? (
                <select
                  value={mapping.source_value}
                  onChange={(event) => void updateMapping(index, { source_value: event.target.value })}
                >
                  <option value="">Select column</option>
                  {sourceColumns.map((column) => (
                    <option key={column.value} value={column.value}>
                      {column.label}
                    </option>
                  ))}
                </select>
              ) : mapping.source_type === 'DERIVED' ? (
                <select
                  value={mapping.source_value}
                  onChange={(event) => void updateMapping(index, { source_value: event.target.value })}
                >
                  <option value="">Select derivation</option>
                  {derivColumns.map((column) => (
                    <option key={column} value={column}>
                      {column}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={mapping.source_value}
                  onChange={(event) => void updateMapping(index, { source_value: event.target.value })}
                />
              )}
            </FormField>
            <FormField label="cast_to">
              <select
                value={mapping.cast_to}
                onChange={(event) =>
                  void updateMapping(index, { cast_to: event.target.value as MappingState['cast_to'] })
                }
              >
                {CAST_TYPES.map((cast) => (
                  <option key={cast} value={cast}>
                    {cast}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Nullable">
              <input
                type="checkbox"
                checked={mapping.is_nullable}
                onChange={(event) => void updateMapping(index, { is_nullable: event.target.checked })}
              />
            </FormField>
          </div>
        ))}
      </Card>
    </>
  )
}

export function useMappingContext(session: ReturnType<typeof useWizard>['session'], blueprintIndex = 0) {
  const blueprint = session?.blueprints[blueprintIndex]
  const columns =
    session?.sources.flatMap((source) =>
      source.columns.map((column) => `${source.alias}.${column.name}`),
    ) ?? []
  const derivs =
    blueprint?.derivations
      .map((item) => (typeof item.variable_name === 'string' ? `deriv.${item.variable_name}` : null))
      .filter((item): item is string => Boolean(item)) ?? []
  return [...columns, ...derivs]
}
