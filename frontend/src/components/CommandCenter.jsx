import React, { useState } from 'react';

const CommandCenter = () => {
    const [status, setStatus] = useState('idle');
    const [activePortal, setActivePortal] = useState(null);

    const runPortal = async (name) => {
        setStatus('running');
        setActivePortal(name);
        try {
            const response = await fetch(`http://localhost:5000/api/run/portal/${name}`, { method: 'POST' });
            const data = await response.json();
            console.log(`Portal ${name} result:`, data);
            alert(`Portal ${name} cycle complete!`);
        } catch (err) {
            alert(`Error running portal ${name}`);
        } finally {
            setStatus('idle');
            setActivePortal(null);
        }
    };

    const toggleMonitoring = async (action) => {
        try {
            await fetch(`http://localhost:5000/api/monitor/${action}`, { method: 'POST' });
            alert(`Monitoring ${action === 'start' ? 'started' : 'stopped'}`);
        } catch (err) {
            alert(`Error changing monitoring status`);
        }
    };

    const portalActions = [
        { id: 'hhsc', name: 'HHSC Portal', icon: '🏥', desc: 'Monitor Texas DIR/HHSC solicitations' },
        { id: 'vms', name: 'VMS Portal', icon: '💼', desc: 'Scan Vendor Management Systems' },
        { id: 'odoo', name: 'Odoo Sync', icon: '🔄', desc: 'Force sync jobs with Odoo CRM' },
        { id: 'dual_table', name: 'Due List', icon: '📊', desc: 'Generate daily Dual Table report' },
    ];

    return (
        <div className="command-view">
            <header className="view-header">
                <h1 className="gradient-text">Command Center</h1>
                <p>Control background automation and manual processing cycles</p>
            </header>

            <div className="controls-grid">
                <div className="main-controls glass-panel">
                    <h3>Continuous Monitoring</h3>
                    <p>Toggle the 24/7 background watcher service</p>
                    <div className="btn-group">
                        <button className="gradient-btn" onClick={() => toggleMonitoring('start')}>Start Watcher</button>
                        <button className="btn-secondary" onClick={() => toggleMonitoring('stop')}>Stop Watcher</button>
                    </div>
                </div>

                <div className="quick-actions glass-panel">
                    <h3>Manual Portal Runs</h3>
                    <div className="portals-list">
                        {portalActions.map((portal) => (
                            <div key={portal.id} className="portal-item">
                                <div className="portal-info">
                                    <span className="portal-icon">{portal.icon}</span>
                                    <div>
                                        <h4>{portal.name}</h4>
                                        <p>{portal.desc}</p>
                                    </div>
                                </div>
                                <button
                                    className={`run-btn ${activePortal === portal.id ? 'loading' : ''}`}
                                    onClick={() => runPortal(portal.id)}
                                    disabled={status === 'running'}
                                >
                                    {activePortal === portal.id ? 'Running...' : 'Run Now'}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <style jsx="true">{`
        .command-view { display: flex; flex-direction: column; gap: 32px; }
        .controls-grid { display: grid; grid-template-columns: 1fr 1.5fr; gap: 24px; }
        .glass-panel { padding: 24px; }
        h3 { margin-bottom: 12px; font-size: 18px; }
        p { color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; }
        
        .btn-group { display: flex; gap: 12px; }
        .btn-secondary { 
            background: rgba(239, 68, 68, 0.1); 
            border: 1px solid var(--accent-danger); 
            color: var(--accent-danger); 
            padding: 10px 20px; 
            border-radius: 8px; 
            font-weight: 600; 
            cursor: pointer;
        }

        .portals-list { display: flex; flex-direction: column; gap: 16px; }
        .portal-item { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            padding: 16px; 
            background: rgba(255,255,255,0.03); 
            border-radius: 12px; 
            border: 1px solid var(--glass-border);
        }
        .portal-info { display: flex; gap: 16px; align-items: center; }
        .portal-icon { font-size: 24px; }
        .portal-info h4 { margin-bottom: 2px; }
        .portal-info p { margin-bottom: 0; font-size: 12px; }
        
        .run-btn { 
            background: var(--glass-border); 
            border: 1px solid var(--text-secondary); 
            color: white; 
            padding: 8px 16px; 
            border-radius: 6px; 
            cursor: pointer; 
            font-size: 13px;
            transition: all 0.2s;
        }
        .run-btn:hover { background: var(--accent-primary); border-color: var(--accent-primary); }
        .run-btn.loading { opacity: 0.7; cursor: not-allowed; }
      `}</style>
        </div>
    );
};

export default CommandCenter;
