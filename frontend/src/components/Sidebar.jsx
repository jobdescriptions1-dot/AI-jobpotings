import React from 'react';

const Sidebar = ({ activeTab, setActiveTab }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'jobs', label: 'Job Postings', icon: '💼' },
    { id: 'chat', label: 'AI Chat', icon: '🤖' },
    { id: 'automation', label: 'Automation', icon: '⚙️' },
  ];

  return (
    <div className="sidebar glass-panel">
      <div className="logo-section" style={{ padding: '20px 16px', marginBottom: '10px' }}>
        <h2 className="gradient-text" style={{ fontSize: '22px', fontWeight: '800', margin: 0 }}>AutoProcure</h2>
        <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>v1.0.0</p>
      </div>

      <nav className="menu-items">
        {menuItems.map((item) => (
          <div
            key={item.id}
            className={`menu-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
          >
            <span className="icon">{item.icon}</span>
            <span className="label">{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="system-status">
        <div className="status-indicator">
          <div className="dot pulse"></div>
          <span>System Live</span>
        </div>
      </div>

    </div>
  );
};

export default Sidebar;
