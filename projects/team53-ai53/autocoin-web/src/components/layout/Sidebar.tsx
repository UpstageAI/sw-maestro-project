import { NavLink } from 'react-router-dom';
import {
  Settings,
  LayoutDashboard,
  ShoppingCart,
  FileText,
} from 'lucide-react';
import styles from './Sidebar.module.css';

const NAV_ITEMS = [
  { to: '/settings', label: '환경 설정', icon: Settings },
  { to: '/dashboard', label: '대시보드', icon: LayoutDashboard },
  { to: '/orders', label: '주문 테스트', icon: ShoppingCart },
  { to: '/reports', label: '리포트', icon: FileText },
] as const;

export function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <span className={styles.logoIcon}>C</span>
        <span className={styles.logoText}>Coin Agent</span>
      </div>
      <nav className={styles.nav}>
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `${styles.navItem} ${isActive ? styles.active : ''}`
            }
          >
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className={styles.footer}>
        <span className={styles.footerLabel}>Testnet Only</span>
      </div>
    </aside>
  );
}
