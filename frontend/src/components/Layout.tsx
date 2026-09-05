import type { ReactNode } from "react";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">RealRails Agentic AI</p>
          <h1>COIP</h1>
          <p>Clinic Operations Intelligence Platform</p>
        </div>
        <nav>
            <a href="#dashboard">Dashboard</a>
            <a href="#requests">Appointment Requests</a>
            <a href="#safety">Safety Boundary</a>
            <a href="#console" className="nav-console-link">Agent Workflow Console</a>
            <a href="#conditional-routing" className="nav-console-link">Conditional Routing</a>
        </nav>
      </aside>
      <main>{children}</main>
    </div>
  );
}
