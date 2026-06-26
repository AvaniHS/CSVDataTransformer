import styles from './ui.module.css'

export function ValidationBanner({ tone, message }: { tone: 'success' | 'warning' | 'error'; message: string }) {
  return <div className={`${styles.banner} ${styles[tone]}`}>{message}</div>
}
