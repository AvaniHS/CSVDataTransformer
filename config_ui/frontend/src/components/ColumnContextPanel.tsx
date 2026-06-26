import styles from './context.module.css'

export function ColumnContextPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <aside className={styles.panel} aria-label={title}>
      <h4>{title}</h4>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>
              <code>{item}</code>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.empty}>No columns available yet.</p>
      )}
    </aside>
  )
}
