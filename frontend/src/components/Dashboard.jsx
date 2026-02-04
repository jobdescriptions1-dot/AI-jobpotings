import React, { useState, useEffect } from 'react';

const Dashboard = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch('http://localhost:5000/rag/stats')
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error('Error fetching stats:', err));
  }, []);

  const statCards = [
    { title: 'Total Jobs', value: stats?.sqlite_db?.total_jobs ?? '0', icon: '💼', color: 'var(--accent-primary)' },
    { title: 'Active Jobs', value: stats?.sqlite_db?.active_jobs ?? '0', icon: '✅', color: 'var(--accent-success)' },
    { title: 'Closed Jobs', value: stats?.sqlite_db?.expired_jobs ?? '0', icon: '⏳', color: 'var(--accent-danger)' },
    { title: 'Odoo Postings (Today)', value: stats?.sqlite_db?.postings_today ?? '0', icon: '📤', color: 'var(--accent-secondary)' },
  ];

  return (
    <div className="dashboard-view" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <header className="view-header" style={{ marginBottom: '24px' }}>
        <h1 className="gradient-text" style={{ fontSize: '32px', fontWeight: '800', margin: '0 0 8px 0' }}>System Overview</h1>
        <p style={{ fontSize: '15px', color: 'var(--text-secondary)', margin: 0 }}>Real-time status of your procurement automation</p>
      </header>

      <div className="stats-grid" style={{
        display: 'flex',
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: '20px',
        width: '100%'
      }}>
        {statCards.map((card, i) => (
          <div key={i} className="stat-card glass-panel" style={{
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            gap: '20px',
            padding: '24px',
            borderRadius: '16px',
            flex: '1',
            minWidth: '280px',
            maxWidth: '350px'
          }}>
            <div className="card-icon" style={{
              background: `${card.color}15`,
              color: card.color,
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '22px',
              boxShadow: `0 4px 8px ${card.color}10`,
              flexShrink: 0
            }}>
              {card.icon}
            </div>
            <div className="card-info">
              <h3 style={{ fontSize: '26px', fontWeight: '800', margin: 0, color: 'var(--text-primary)', lineHeight: '1.2' }}>{card.value}</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '11px', fontWeight: '600', margin: '2px 0 0 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{card.title}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="project-description-section glass-panel" style={{
        padding: '32px',
        borderRadius: '16px',
        marginTop: '8px'
      }}>
        <h2 style={{ fontSize: '20px', fontWeight: '700', margin: '0 0 16px 0', color: 'var(--text-primary)' }}>About Procurement Automation System</h2>
        <div style={{ lineHeight: '1.6', color: 'var(--text-secondary)', fontSize: '15px' }}>
          <p style={{ margin: '0 0 12px 0' }}>
            This system streamlines the recruitment lifecycle by automating the ingestion and processing of job requisitions.
            It monitors incoming VMS communications, extracts technical requirements using specialized processors,
            and utilizes Retrieval-Augmented Generation (RAG) to provide intelligent search and analysis capabilities.
          </p>
          <p style={{ margin: 0 }}>
            By synchronizing verified job data with <strong>Odoo</strong>, the platform ensures that your talent pipeline
            remains up-to-date with minimal manual intervention, allowing your team to focus on high-value candidate engagement.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
