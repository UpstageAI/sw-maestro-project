import styles from './Spinner.module.css';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
}

export function Spinner({ size = 'md' }: SpinnerProps) {
  return (
    <div className={styles.container} role="status" aria-label="로딩 중">
      <div className={`${styles.spinner} ${styles[size]}`} />
    </div>
  );
}
