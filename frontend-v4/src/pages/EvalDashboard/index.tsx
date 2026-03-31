/**
 * Eval Dashboard — Three-tab view for creation, verification, and calibration eval results.
 * Data-driven: tabs, scores, and columns render from whatever the reports contain.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AGENT_TABS } from './types';
import type { AgentType } from './types';
import AgentTab from './components/AgentTab';

export default function EvalDashboard() {
  const [activeTab, setActiveTab] = useState<AgentType>('unified');

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem', background: '#0f172a', color: '#e2e8f0', minHeight: '100vh', borderRadius: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <Link to="/" style={{ textDecoration: 'none', fontSize: '1.2rem', color: '#60a5fa' }}>← Back</Link>
        <h1 style={{ margin: 0, color: '#f1f5f9' }}>Eval Dashboard</h1>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '2px solid #334155' }}>
        {AGENT_TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '0.5rem 1rem',
              border: 'none',
              borderBottom: activeTab === tab.key ? '3px solid #3b82f6' : '3px solid transparent',
              background: activeTab === tab.key ? '#1e293b' : 'transparent',
              color: activeTab === tab.key ? '#fff' : '#94a3b8',
              cursor: 'pointer',
              fontWeight: activeTab === tab.key ? 600 : 400,
              fontSize: '0.95rem',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <AgentTab agentType={activeTab} />
    </div>
  );
}
