import React, { useState, useEffect } from 'react';

const JobPostings = () => {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedJob, setSelectedJob] = useState(null);

    // Filters
    const [filters, setFilters] = useState({
        title: '',
        location: '',
        job_id: '',
        status: '', // active or expired
        due_date: '',
    });

    const formatDate = (dateStr) => {
        if (!dateStr || dateStr === 'N/A') return 'N/A';
        try {
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return dateStr;
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: '2-digit',
                year: 'numeric'
            });
        } catch (e) {
            return dateStr;
        }
    };

    const [syncMessage, setSyncMessage] = useState("");

    const fetchJobs = () => {
        setLoading(true);
        const queryParams = new URLSearchParams();
        if (filters.title) queryParams.append('title', filters.title);
        if (filters.location) queryParams.append('location', filters.location);
        if (filters.job_id) queryParams.append('job_id', filters.job_id);
        if (filters.status) queryParams.append('status', filters.status);
        if (filters.due_date) queryParams.append('due_date_after', filters.due_date);

        fetch(`http://localhost:5000/rag/jobs?${queryParams.toString()}&limit=50`)
            .then(res => res.json())
            .then(data => {
                setJobs(data.jobs || []);
                setLoading(false);
            })
            .catch(err => {
                console.error('Error fetching jobs:', err);
                setLoading(false);
            });
    };

    useEffect(() => {
        fetchJobs();
    }, [filters.status, filters.title, filters.location, filters.job_id, filters.due_date]); // Refetch on any filter change

    const syncJobs = async () => {
        try {
            setLoading(true);
            setSyncMessage("Posting local jobs to Odoo...");

            // 1. Run Odoo Posting
            const postRes = await fetch('http://localhost:5000/api/run/portal/odoo', { method: 'POST' });
            if (!postRes.ok) throw new Error("Odoo Posting failed");

            setSyncMessage("Fetching new jobs from Odoo...");

            // 2. Run RAG Ingestion from Odoo
            const ingestRes = await fetch('http://localhost:5000/rag/ingest-odoo', { method: 'POST' });
            if (!ingestRes.ok) throw new Error("Odoo Ingestion failed");

            const data = await ingestRes.json();
            setSyncMessage(`Success: Synced ${data.count || 0} jobs`);

            setTimeout(() => {
                setSyncMessage("");
                fetchJobs(); // Refetch jobs after sync
            }, 2000);
        } catch (err) {
            console.error('Error syncing jobs:', err);
            setSyncMessage(`⚠️ Sync Failed: ${err.message}`);
            setTimeout(() => {
                setLoading(false);
                setSyncMessage("");
            }, 5000);
        }
    };

    // Helper for safe job ID display
    const formatJobId = (id) => {
        if (!id) return 'N/A';
        const strId = String(id);
        return strId.includes('-') ? strId.split('-').pop() : strId;
    };

    return (
        <div className="job-postings-view">
            <header className="view-header">
                <div className="header-top">
                    <div>
                        <h1 className="gradient-text">Job Postings</h1>
                        <p>Live job requisitions from Odoo ERP</p>
                    </div>
                    <div className="header-actions">
                        <button
                            className={`ghost-btn ${filters.status === 'expired' ? 'active' : ''}`}
                            onClick={() => setFilters({ ...filters, status: filters.status === 'expired' ? '' : 'expired' })}
                        >
                            🕒 Expired Jobs
                        </button>
                        <button
                            className="white-btn"
                            onClick={syncJobs}
                            disabled={loading}
                        >
                            {loading ? `⏳ ${syncMessage || 'Syncing...'}` : '🔄 Sync Jobs'}
                        </button>
                    </div>
                </div>

                <div className="filter-bar glass-panel">
                    <div className="filter-input">
                        <span className="icon">🔍</span>
                        <input
                            type="text"
                            placeholder="Title..."
                            value={filters.title}
                            onChange={(e) => setFilters({ ...filters, title: e.target.value })}
                            onKeyPress={(e) => e.key === 'Enter' && fetchJobs()}
                        />
                    </div>
                    <div className="filter-input">
                        <span className="icon">📍</span>
                        <input
                            type="text"
                            placeholder="Location..."
                            value={filters.location}
                            onChange={(e) => setFilters({ ...filters, location: e.target.value })}
                            onKeyPress={(e) => e.key === 'Enter' && fetchJobs()}
                        />
                    </div>
                    <div className="filter-input">
                        <span className="icon">#</span>
                        <input
                            type="text"
                            placeholder="Job ID..."
                            value={filters.job_id}
                            onChange={(e) => setFilters({ ...filters, job_id: e.target.value })}
                            onKeyPress={(e) => e.key === 'Enter' && fetchJobs()}
                        />
                    </div>
                    <div className="filter-input">
                        <span className="icon">📅</span>
                        <input
                            type="date"
                            style={{ colorScheme: 'dark' }}
                            value={filters.due_date}
                            onChange={(e) => setFilters({ ...filters, due_date: e.target.value })}
                        />
                    </div>
                </div>
            </header>

            <div className="jobs-list">
                {loading ? (
                    <div className="loading-state">Loading job requisitions...</div>
                ) : jobs.length === 0 ? (
                    <div className="empty-state">
                        {filters.status === 'expired'
                            ? "No expired jobs found. All current requisitions are active."
                            : "No jobs match your search criteria."}
                    </div>
                ) : (
                    jobs.map((job) => (
                        <div key={job.job_id} className="job-card glass-panel" onClick={() => setSelectedJob(job)}>
                            <div className="card-left">
                                <div className="briefcase-icon">💼</div>
                            </div>
                            <div className="card-center">
                                <h2>{job.title}</h2>
                                <div className="card-subtext">
                                    <span>📍 {job.location || job.state || 'N/A'}</span>
                                    <span className="dot">•</span>
                                    <span>👤 {Math.floor(Math.random() * 5)} Applicants</span>
                                    <span className="dot">•</span>
                                    <span>📅 Due {formatDate(job.tracking_due_date || job.due_date)}</span>
                                </div>
                            </div>
                            <div className="card-right">
                                <span className="job-id-text" style={{ fontSize: '18px', fontWeight: '700' }}>#{formatJobId(job.job_id)}</span>
                                <span className={`status-badge ${job.status?.toLowerCase()}`} style={{ fontSize: '13px', padding: '6px 14px' }}>
                                    {(job.status === 'Active' || !job.status) ? '● Active' : '● Closed'}
                                </span>
                                <div className="external-icon">↗️</div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {selectedJob && (
                <div className="modal-overlay" onClick={() => setSelectedJob(null)}>
                    <div className="modal-content glass-panel" onClick={e => e.stopPropagation()}>
                        <button className="close-btn" onClick={() => setSelectedJob(null)}>×</button>
                        <h2 className="gradient-text">{selectedJob.title}</h2>
                        <div className="modal-meta">
                            <span>ID: {selectedJob.job_id}</span>
                            <span>Location: {selectedJob.location || selectedJob.state || 'N/A'}</span>
                            <span>Status: {selectedJob.status || 'Active'}</span>
                            <span>📅 Due {formatDate(selectedJob.tracking_due_date || selectedJob.due_date)}</span>
                        </div>
                        <div className="description-box">
                            <h3>Job Description</h3>
                            <div className="desc-scroll">
                                {selectedJob.description || "No detailed description available."}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default JobPostings;
