import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { ConsolePage } from "./pages/ConsolePage";
import ConditionalRoutingConsole from "./pages/ConditionalRoutingConsole";

export default function App() {
  // Stage 1.5 addition: minimal hash-based page switch. Only "#console"
  // switches pages; every other hash (including the existing #dashboard,
  // #requests, #safety anchors) continues to behave exactly as before,
  // scrolling within the unchanged Dashboard page.
  //
  // Stage 3.1 addition: same pattern extended for "#conditional-routing".
  const [isConsole, setIsConsole] = useState(() => window.location.hash.startsWith("#console"));
  const [isConditionalRouting, setIsConditionalRouting] = useState(() =>
    window.location.hash.startsWith("#conditional-routing")
  );

  useEffect(() => {
    const onHashChange = () => {
      setIsConsole(window.location.hash.startsWith("#console"));
      setIsConditionalRouting(window.location.hash.startsWith("#conditional-routing"));
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return (
    <Layout>
      {isConditionalRouting ? (
        <ConditionalRoutingConsole />
      ) : isConsole ? (
        <ConsolePage />
      ) : (
        <DashboardPage />
      )}
    </Layout>
  );
}