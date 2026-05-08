import styles from './Skeleton.module.css';

interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
}

export function Skeleton({
  width = '100%',
  height = '20px',
  borderRadius,
}: SkeletonProps) {
  return (
    <div
      className={styles.skeleton}
      style={{ width, height, borderRadius: borderRadius ?? 'var(--radius-sm)' }}
      aria-hidden="true"
    />
  );
}
