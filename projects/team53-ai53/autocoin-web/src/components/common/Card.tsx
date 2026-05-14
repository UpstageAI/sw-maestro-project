import type { HTMLAttributes, ReactNode } from 'react';
import styles from './Card.module.css';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  padding?: 'sm' | 'md' | 'lg';
}

export function Card({
  title,
  subtitle,
  actions,
  padding = 'md',
  children,
  className,
  ...rest
}: CardProps) {
  const classNames = [styles.card, styles[padding], className ?? '']
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classNames} {...rest}>
      {(title || actions) && (
        <div className={styles.header}>
          <div className={styles.headerText}>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {actions && <div className={styles.actions}>{actions}</div>}
        </div>
      )}
      <div className={styles.body}>{children}</div>
    </div>
  );
}
