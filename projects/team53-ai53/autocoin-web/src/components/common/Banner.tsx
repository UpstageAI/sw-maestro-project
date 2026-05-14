import { AlertTriangle, Info, XCircle, CheckCircle } from 'lucide-react';
import type { ReactNode } from 'react';
import styles from './Banner.module.css';

type BannerVariant = 'info' | 'warning' | 'danger' | 'success';

interface BannerProps {
  variant?: BannerVariant;
  children: ReactNode;
}

const iconMap = {
  info: Info,
  warning: AlertTriangle,
  danger: XCircle,
  success: CheckCircle,
};

export function Banner({ variant = 'info', children }: BannerProps) {
  const Icon = iconMap[variant];
  const classNames = [styles.banner, styles[variant]].join(' ');

  return (
    <div className={classNames} role="alert">
      <Icon size={18} className={styles.icon} aria-hidden="true" />
      <div className={styles.content}>{children}</div>
    </div>
  );
}
