import styles from './schema.module.css'

export function SchemaTable({
  columns,
  rows,
}: {
  columns: string[]
  rows: Record<string, string>[]
}) {
  if (!columns.length) {
    return <p className={styles.empty}>No columns detected.</p>
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{row[column] ?? ''}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
