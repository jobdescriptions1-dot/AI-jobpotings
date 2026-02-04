import React, { useState, useEffect } from 'react';

const JobsTable = () => {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://localhost:5000/rag/jobs?limit=50')
            .then(res => res.json())
            .then(data => {
                setJobs(data.jobs || []);
                setLoading(false);
            })
            .catch(err => {
                console.error('Error fetching jobs:', err);
                setLoading(false);
            });
    }, []);

    return (
        <div className="jobs-view">
            <header className="view-header">
                <h1 className="gradient-text">Job Tracker</h1>
                <p>Manage and view all processed government procurements</p>
            </header>

            <div className="table-container glass-panel">
                <table className="jobs-table">
                    <thead>
                        <tr>
                            <th>Job ID</th>
                            <th>Title</th>
                            <th>State</th>
                            <th>Mode</th>
                            <th>Due Date</th>
                            <th>Odoo status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px' }}>Loading jobs...</td></tr>
                        ) : jobs.length === 0 ? (
                            <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px' }}>No jobs found.</td></tr>
                        ) : (
                            jobs.map((job) => (
                                <tr key={job.job_id}>
                                    <td className="job-id">{job.job_id}</td>
                                    <td className="job-title">{job.title}</td>
                                    <td><span className="badge state">{job.state || 'N/A'}</span></td>
                                    <td>{job.work_mode || 'Onsite'}</td>
                                    <td className="due-date">{job.tracking_due_date || job.due_date || 'N/A'}</td>
                                    <td>
                                        <span className={`badge ${job.last_posting_time ? 'success' : 'pending'}`}>
                                            {job.last_posting_time ? 'Posted' : 'Pending'}
                                        </span>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <style jsx="true">{`
        .jobs-view { display: flex; flex-direction: column; gap: 32px; height: 100%; }
        .table-container { overflow: hidden; }
        .jobs-table { width: 100%; border-collapse: collapse; text-align: left; }
        th { padding: 16px 24px; color: var(--text-secondary); font-weight: 600; font-size: 14px; border-bottom: 1px solid var(--glass-border); }
        td { padding: 16px 24px; border-bottom: 1px solid var(--glass-border); font-size: 14px; }
        tr:hover { background: rgba(255,255,255,0.02); }
        .job-id { font-family: var(--font-mono); color: var(--accent-primary); font-weight: 500; }
        .job-title { font-weight: 600; }
        .badge { padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }
        .badge.state { background: rgba(99, 102, 241, 0.1); color: var(--accent-primary); }
        .badge.success { background: rgba(16, 185, 129, 0.1); color: var(--accent-success); }
        .badge.pending { background: rgba(245, 158, 11, 0.1); color: var(--accent-warning); }
        .due-date { color: var(--accent-danger); font-weight: 500; }
      `}</style>
        </div>
    );
};

export default JobsTable;
