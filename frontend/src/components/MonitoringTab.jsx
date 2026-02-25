import { useState, useEffect } from "react";
import "./MonitoringTab.css";

// Fallback data when API is unavailable
const FALLBACK_ORGANS = [
  {
    id: "self-healing",
    name: "Self Healing",
    percentage: 15,
    color: "#ef4444",
    icon: (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        fill="currentColor"
        className="bi bi-bandaid"
        viewBox="0 0 16 16"
      >
        <path d="M14.121 1.879a3 3 0 0 0-4.242 0L8.733 3.026l4.261 4.26 1.127-1.165a3 3 0 0 0 0-4.242M12.293 8 8.027 3.734 3.738 8.031 8 12.293zm-5.006 4.994L3.03 8.737 1.879 9.88a3 3 0 0 0 4.241 4.24l.006-.006 1.16-1.121ZM2.679 7.676l6.492-6.504a4 4 0 0 1 5.66 5.653l-1.477 1.529-5.006 5.006-1.523 1.472a4 4 0 0 1-5.653-5.66l.001-.002 1.505-1.492z" />
        <path d="M5.56 7.646a.5.5 0 1 1-.706.708.5.5 0 0 1 .707-.708Zm1.415-1.414a.5.5 0 1 1-.707.707.5.5 0 0 1 .707-.707M8.39 4.818a.5.5 0 1 1-.708.707.5.5 0 0 1 .707-.707Zm0 5.657a.5.5 0 1 1-.708.707.5.5 0 0 1 .707-.707ZM9.803 9.06a.5.5 0 1 1-.707.708.5.5 0 0 1 .707-.707Zm1.414-1.414a.5.5 0 1 1-.706.708.5.5 0 0 1 .707-.708ZM6.975 9.06a.5.5 0 1 1-.707.708.5.5 0 0 1 .707-.707ZM8.39 7.646a.5.5 0 1 1-.708.708.5.5 0 0 1 .707-.708Zm1.413-1.414a.5.5 0 1 1-.707.707.5.5 0 0 1 .707-.707" />
      </svg>
    ),
  },
  {
    id: "world-model",
    name: "World Model",
    percentage: 30,
    color: "#3b82f6",
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        <circle cx="12" cy="12" r="1" />
      </svg>
    ),
  },
  {
    id: "self-learning",
    name: "Self Learning",
    percentage: 5,
    color: "#f59e0b",
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        <path d="M10 6h6M10 10h6M10 14h3" />
      </svg>
    ),
  },
  {
    id: "self-governance",
    name: "Self Governance",
    percentage: 0,
    color: "#8b5cf6",
    icon: (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        fill="currentColor"
        className="bi bi-shield-check"
        viewBox="0 0 16 16"
      >
        <path d="M5.338 1.59a61 61 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.7 10.7 0 0 0 2.287 2.233c.346.244.652.42.893.533q.18.085.293.118a1 1 0 0 0 .101.025 1 1 0 0 0 .1-.025q.114-.034.294-.118c.24-.113.547-.29.893-.533a10.7 10.7 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524zM5.072.56C6.157.265 7.31 0 8 0s1.843.265 2.928.56c1.11.3 2.229.655 2.887.87a1.54 1.54 0 0 1 1.044 1.262c.596 4.477-.787 7.795-2.465 9.99a11.8 11.8 0 0 1-2.517 2.453 7 7 0 0 1-1.048.625c-.28.132-.581.24-.829.24s-.548-.108-.829-.24a7 7 0 0 1-1.048-.625 11.8 11.8 0 0 1-2.517-2.453C1.928 10.487.545 7.169 1.141 2.692A1.54 1.54 0 0 1 2.185 1.43 63 63 0 0 1 5.072.56" />
        <path d="M10.854 5.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 7.793l2.646-2.647a.5.5 0 0 1 .708 0" />
      </svg>
    ),
  },
];

export default function MonitoringTab() {
  const [organs, setOrgans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [overallProgress, setOverallProgress] = useState(0);
  const [_lastUpdated, setLastUpdated] = useState(null);

  const getOrganIcon = (organId) => {
    const icons = {
      'self-healing': (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-bandaid" viewBox="0 0 16 16">
          <path d="M14.121 1.879a3 3 0 0 0-4.242 0L8.733 3.026l4.261 4.26 1.127-1.165a3 3 0 0 0 0-4.242M12.293 8 8.027 3.734 3.738 8.031 8 12.293zm-5.006 4.994L3.03 8.737 1.879 9.88a3 3 0 0 0 4.241 4.24l.006-.006 1.16-1.121ZM2.679 7.676l6.492-6.504a4 4 0 0 1 5.66 5.653l-1.477 1.529-5.006 5.006-1.523 1.472a4 4 0 0 1-5.653-5.66l.001-.002 1.505-1.492z" />
          <path d="M5.56 7.646a.5.5 0 1 1-.706.708.5.5 0 0 1 .707-.708Zm1.415-1.414a.5.5 0 1 1-.707.707.5.5 0 0 1 .707-.707M8.39 4.818a.5.5 0 1 1-.708.707.5.5 0 0 1 .707-.707Zm0 5.657a.5.5 0 1 1-.708.707.5.5 0 0 1 .707-.707ZM9.803 9.06a.5.5 0 1 1-.707.708.5.5 0 0 1 .707-.707Zm1.414-1.414a.5.5 0 1 1-.706.708.5.5 0 0 1 .707-.708ZM6.975 9.06a.5.5 0 1 1-.707.708.5.5 0 0 1 .707-.707ZM8.39 7.646a.5.5 0 1 1-.708.708.5.5 0 0 1 .707-.708Zm1.413-1.414a.5.5 0 1 1-.707.707.5.5 0 0 1 .707-.707" />
        </svg>
      ),
      'world-model': (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          <circle cx="12" cy="12" r="1" />
        </svg>
      ),
      'self-learning': (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          <path d="M10 6h6M10 10h6M10 14h3" />
        </svg>
      ),
      'self-governance': (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-shield-check" viewBox="0 0 16 16">
          <path d="M5.338 1.59a61 61 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.7 10.7 0 0 0 2.287 2.233c.346.244.652.42.893.533q.18.085.293.118a1 1 0 0 0 .101.025 1 1 0 0 0 .1-.025q.114-.034.294-.118c.24-.113.547-.29.893-.533a10.7 10.7 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524zM5.072.56C6.157.265 7.31 0 8 0s1.843.265 2.928.56c1.11.3 2.229.655 2.887.87a1.54 1.54 0 0 1 1.044 1.262c.596 4.477-.787 7.795-2.465 9.99a11.8 11.8 0 0 1-2.517 2.453 7 7 0 0 1-1.048.625c-.28.132-.581.24-.829.24s-.548-.108-.829-.24a7 7 0 0 1-1.048-.625 11.8 11.8 0 0 1-2.517-2.453C1.928 10.487.545 7.169 1.141 2.692A1.54 1.54 0 0 1 2.185 1.43 63 63 0 0 1 5.072.56" />
          <path d="M10.854 5.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 7.793l2.646-2.647a.5.5 0 0 1 .708 0" />
        </svg>
      ),
    };
    return icons[organId] || icons['self-healing'];
  };

  const fetchOrgansStatus = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/monitoring/organs');
      if (response.ok) {
        const data = await response.json();
        // Map API response to component format with icons
        const organsWithIcons = (data.organs || []).map(organ => ({
          ...organ,
          icon: getOrganIcon(organ.id),
        }));
        setOrgans(organsWithIcons);
        setOverallProgress(data.overall_progress || 0);
        setLastUpdated(data.last_updated);
      } else {
        // Use fallback data
        setOrgans(FALLBACK_ORGANS);
      }
    } catch (error) {
      console.error('Error fetching organs status:', error);
      setOrgans(FALLBACK_ORGANS);
    }
    setLoading(false);
  };

  useEffect(() => {
    queueMicrotask(() => fetchOrgansStatus());
  }, []);

  if (loading) {
    return (
      <div className="monitoring-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading system status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="monitoring-tab">
      <div className="monitoring-header">
        <div className="header-left">
          <h2>Organs of Grace - Development Progress</h2>
          <p className="monitoring-subtitle">
            Track the implementation progress of core system organs
          </p>
        </div>
        <div className="header-right">
          <div className="overall-progress">
            <span className="progress-label">Overall Progress</span>
            <span className="progress-value">{overallProgress.toFixed(1)}%</span>
          </div>
          <button className="btn-refresh" onClick={fetchOrgansStatus}>
            Refresh
          </button>
        </div>
      </div>

      <div className="organs-grid">
        {organs.map((organ) => (
          <div key={organ.id} className="organ-card">
            <div className="organ-icon" style={{ color: organ.color }}>
              {organ.icon}
            </div>

            <div className="organ-info">
              <h3>{organ.name}</h3>
              <p className="organ-percentage">{organ.percentage}%</p>
            </div>

            <div className="liquid-fill-container">
              <svg
                className="liquid-fill-svg"
                viewBox="0 0 200 200"
                preserveAspectRatio="xMidYMid meet"
              >
                <defs>
                  <clipPath id={`clip-${organ.id}`}>
                    <rect x="20" y="20" width="160" height="160" rx="8" />
                  </clipPath>

                  <linearGradient
                    id={`grad-${organ.id}`}
                    x1="0%"
                    y1="0%"
                    x2="0%"
                    y2="100%"
                  >
                    <stop offset="0%" stopColor={organ.color} stopOpacity="1" />
                    <stop
                      offset="100%"
                      stopColor={organ.color}
                      stopOpacity="0.7"
                    />
                  </linearGradient>

                  <filter id={`shadow-${organ.id}`}>
                    <feDropShadow
                      dx="0"
                      dy="1"
                      stdDeviation="1"
                      floodOpacity="0.3"
                    />
                  </filter>
                </defs>

                {/* Background container box */}
                <rect
                  x="20"
                  y="20"
                  width="160"
                  height="160"
                  rx="8"
                  fill="none"
                  stroke={organ.color}
                  strokeWidth="1.5"
                  opacity="0.35"
                />

                {/* Container fill background */}
                <g clipPath={`url(#clip-${organ.id})`}>
                  <rect
                    x="20"
                    y="20"
                    width="160"
                    height="160"
                    fill={organ.color}
                    opacity="0.02"
                  />

                  {/* Liquid base fill */}
                  <rect
                    x="20"
                    y={20 + 160 - (160 * organ.percentage) / 100}
                    width="160"
                    height={(160 * organ.percentage) / 100}
                    fill={`url(#grad-${organ.id})`}
                    className="liquid-base"
                  />

                  {/* Animated wave surfaces */}
                  {organ.percentage > 0 && (
                    <>
                      {/* First wave layer */}
                      <path
                        className="wave-path wave-1"
                        d={`M20,${20 + 160 - (160 * organ.percentage) / 100}
                           Q40,${
                             20 + 160 - (160 * organ.percentage) / 100 - 5
                           },60,${20 + 160 - (160 * organ.percentage) / 100}
                           T100,${20 + 160 - (160 * organ.percentage) / 100}
                           T140,${20 + 160 - (160 * organ.percentage) / 100}
                           T180,${20 + 160 - (160 * organ.percentage) / 100}
                           L180,${20 + 160}
                           L20,${20 + 160}
                           Z`}
                        fill={organ.color}
                        opacity="0.8"
                        filter={`url(#shadow-${organ.id})`}
                        style={{
                          "--wave-y": `${
                            20 + 160 - (160 * organ.percentage) / 100
                          }px`,
                        }}
                      />

                      {/* Second wave layer with delay */}
                      <path
                        className="wave-path wave-2"
                        d={`M20,${20 + 160 - (160 * organ.percentage) / 100 - 2}
                           Q40,${
                             20 + 160 - (160 * organ.percentage) / 100 - 7
                           },60,${20 + 160 - (160 * organ.percentage) / 100 - 2}
                           T100,${20 + 160 - (160 * organ.percentage) / 100 - 2}
                           T140,${20 + 160 - (160 * organ.percentage) / 100 - 2}
                           T180,${20 + 160 - (160 * organ.percentage) / 100 - 2}
                           L180,${20 + 160}
                           L20,${20 + 160}
                           Z`}
                        fill={organ.color}
                        opacity="0.5"
                      />

                      {/* Third wave layer for shimmer */}
                      <path
                        className="wave-path wave-3"
                        d={`M20,${20 + 160 - (160 * organ.percentage) / 100 - 3}
                           Q40,${
                             20 + 160 - (160 * organ.percentage) / 100 - 6
                           },60,${20 + 160 - (160 * organ.percentage) / 100 - 3}
                           T100,${20 + 160 - (160 * organ.percentage) / 100 - 3}
                           T140,${20 + 160 - (160 * organ.percentage) / 100 - 3}
                           T180,${20 + 160 - (160 * organ.percentage) / 100 - 3}
                           L180,${20 + 160}
                           L20,${20 + 160}
                           Z`}
                        fill={organ.color}
                        opacity="0.25"
                      />
                    </>
                  )}
                </g>
              </svg>

              <div className="fill-percentage">
                <span className="percentage-text">{organ.percentage}%</span>
              </div>
            </div>

            <div className="organ-status">
              {organ.percentage === 0 && (
                <span className="status-badge not-started">Not Started</span>
              )}
              {organ.percentage > 0 && organ.percentage < 50 && (
                <span className="status-badge in-progress">In Progress</span>
              )}
              {organ.percentage >= 50 && organ.percentage < 100 && (
                <span className="status-badge advanced">Advanced</span>
              )}
              {organ.percentage === 100 && (
                <span className="status-badge completed">Completed</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
