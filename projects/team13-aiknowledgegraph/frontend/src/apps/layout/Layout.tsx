import { Outlet } from 'react-router-dom';

function Layout() {
  return (
    <main className="app-shell">
      <Outlet />
    </main>
  );
}

export default Layout;
