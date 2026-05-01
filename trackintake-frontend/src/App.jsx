import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import UserManagement from "./pages/UserManagement";
import SubscriptionPlans from "./pages/SubscriptionPlans";
import SubscriptionPayments from "./pages/SubscriptionPayments";
import Notifications from "./pages/Notifications";
import Nutritionists from "./pages/Nutritionists";

function PlaceholderPage({ title }) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      <p className="text-sm text-gray-500 mt-1">This section is under construction.</p>
    </div>
  );
}

export default function App() {
  const [activePage, setActivePage] = useState(() => sessionStorage.getItem("activePage") || "dashboard");
  const [pageState, setPageState] = useState({});
  const [unreadCount, setUnreadCount] = useState(0);

  // Fetch unread notification count on load
useEffect(() => {
  const fetchUnread = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/notifications/admin-notifications/?type=admin');
      const data = res.ok ? await res.json() : { unread_count: 0 };
      setUnreadCount(data.unread_count || 0);
    } catch (error) {
      console.error("Notification fetch error:", error);
    }
  };

  fetchUnread(); // pehli baar turant
  const interval = setInterval(fetchUnread, 30000); // har 30 sec mein
  return () => clearInterval(interval); // cleanup
}, []);
  const handleNavigate = (page) => {
    sessionStorage.setItem("activePage", page);
    setActivePage(page);
  };

  useEffect(() => {
    const handleNav = (e) => {
      setPageState(e.detail.state || {});
      handleNavigate(e.detail.page);
    };
    window.addEventListener("app-nav", handleNav);
    return () => window.removeEventListener("app-nav", handleNav);
  }, []);

  const renderPage = () => {
    switch (activePage) {
      case "dashboard": return <Dashboard pageState={pageState} />;
      case "users": return <UserManagement pageState={pageState} />;
      case "plans": return <SubscriptionPlans />;
      case "payments": return <SubscriptionPayments pageState={pageState} />;
      case "nutritionists": return <Nutritionists />;
      case "notifications": return <Notifications onUnreadChange={setUnreadCount} />;
      case "meals": return <PlaceholderPage title="Meals" />;
      case "diet": return <PlaceholderPage title="Diet Plans" />;
      case "progress": return <PlaceholderPage title="Progress" />;
      case "appointments": return <PlaceholderPage title="Appointments" />;
      case "blogs": return <PlaceholderPage title="Blogs" />;
      case "settings": return <PlaceholderPage title="Settings" />;
      default: return <PlaceholderPage title="Page" />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar active={activePage} onNavigate={handleNavigate} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar unreadCount={unreadCount} onNotificationClick={() => handleNavigate("notifications")} />
        <main className="flex-1 overflow-y-auto">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}
