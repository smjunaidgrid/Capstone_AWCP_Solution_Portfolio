import React, { useState, useEffect } from 'react';
import { AlertTriangle, Database, Activity, ShieldCheck } from 'lucide-react';
import axios from 'axios';

function App() {
  // 1. Create a "state" to hold the live data from our Python backend
  const [status, setStatus] = useState({
    degraded_workflows: 0,
    evidence_ledger: 'Connecting...',
    proxy_status: 'Connecting...',
    latest_assessment: 'Awaiting telemetry...' // <-- New state for the feed
  });

  // 2. Set up the polling mechanism (runs every 3 seconds for better real-time feel) 
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get('http://localhost:8000/status');
        setStatus(response.data);
      } catch (error) {
        console.error("Error fetching status from backend", error);
        setStatus({
          degraded_workflows: 0,
          evidence_ledger: 'Offline',
          proxy_status: 'Offline',
          latest_assessment: 'Offline'
        });
      }
    };

    // Fetch immediately when the page loads
    fetchStatus();

    // Then set an interval to fetch every 3 seconds (3000 ms)
    const interval = setInterval(fetchStatus, 3000);

    // Cleanup the interval if we close the page
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '50px', background: '#F2EDE1', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <h1 style={{ color: '#0F0E0C', borderBottom: '2px solid #7A2E1E', paddingBottom: '10px' }}>
        AWCP Operator Surface
      </h1>
      
      <div style={{ display: 'flex', gap: '20px', marginTop: '30px' }}>
        
        {/* Degraded Workflows Card */}
        <div style={{ border: '1px solid #7A2E1E', padding: '20px', borderRadius: '8px', background: '#fff', width: '250px' }}>
          <AlertTriangle color="#7A2E1E" size={32} />
          <h3 style={{ color: '#7A2E1E' }}>Degraded Workflows</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', margin: '10px 0' }}>
            {status.degraded_workflows}
          </p>
          <span style={{ fontSize: '12px', color: '#6B6558' }}>Agents breaching budgets</span>
        </div>

        {/* Evidence Ledger Card */}
        <div style={{ border: '1px solid #265D6B', padding: '20px', borderRadius: '8px', background: '#fff', width: '250px' }}>
          <Database color="#265D6B" size={32} />
          <h3 style={{ color: '#265D6B' }}>Evidence Ledger</h3>
          <p style={{ fontSize: '14px', fontWeight: 'bold', margin: '10px 0' }}>
            {status.evidence_ledger}
          </p>
          <span style={{ fontSize: '12px', color: '#6B6558' }}>Immutable storage active</span>
        </div>

        {/* Intake Proxy Card */}
        <div style={{ border: '1px solid #6B6558', padding: '20px', borderRadius: '8px', background: '#fff', width: '250px' }}>
          <Activity color="#6B6558" size={32} />
          <h3 style={{ color: '#6B6558' }}>Intake Proxy</h3>
          <p style={{ fontSize: '14px', fontWeight: 'bold', margin: '10px 0' }}>
            {status.proxy_status}
          </p>
          <span style={{ fontSize: '12px', color: '#6B6558' }}>Port 8000</span>
        </div>

      </div>

      {/* NEW: Cognitive Shield Live Feed Card */}
      <div style={{ marginTop: '30px', border: '1px solid #265D6B', padding: '20px', borderRadius: '8px', background: '#fff', maxWidth: '790px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
          <ShieldCheck color="#265D6B" size={28} />
          <h3 style={{ color: '#265D6B', margin: 0 }}>Cognitive Shield: Live Replay Summary</h3>
        </div>
        <p style={{ 
          fontSize: '16px', 
          fontWeight: '500', 
          color: '#0F0E0C', 
          background: '#F2EDE1', 
          padding: '15px', 
          borderRadius: '4px', 
          margin: 0,
          borderLeft: '4px solid #265D6B'
        }}>
          {status.latest_assessment}
        </p>
      </div>

    </div>
  );
}

export default App;