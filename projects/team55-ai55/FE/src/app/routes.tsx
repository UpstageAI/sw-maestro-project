import { createBrowserRouter } from "react-router";
import Root from "./Root";
import Login from "./pages/Login";
import NewProject from "./pages/NewProject";
import Dashboard from "./pages/Dashboard";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, Component: Login },
      { path: "new", Component: NewProject },
      { path: "dashboard", Component: Dashboard },
      { path: "projects", Component: Dashboard },
      { path: "projects/:projectId", Component: Dashboard },
      { path: "projects/:projectId/setup", Component: Dashboard },
      { path: "projects/:projectId/tasks", Component: Dashboard },
      { path: "projects/:projectId/calendar", Component: Dashboard },
      { path: "projects/:projectId/settings", Component: Dashboard },
    ],
  },
]);
