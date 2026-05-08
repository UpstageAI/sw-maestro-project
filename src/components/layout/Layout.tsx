import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBanner } from './TopBanner';
import styles from './Layout.module.css';

export function Layout() {
  return (
    <div className={styles.layout}>
      <TopBanner />
      <div className={styles.container}>
        <Sidebar />
        <main className={styles.main}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
