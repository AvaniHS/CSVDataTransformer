import styles from './ui.module.css'

export function Card({ title, children, className = '' }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`${styles.card} ${className}`}>
      {title ? <h3 className={styles.cardTitle}>{title}</h3> : null}
      {children}
    </section>
  )
}
