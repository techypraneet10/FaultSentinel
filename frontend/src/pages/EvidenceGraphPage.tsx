import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';

export const EvidenceGraphPage: React.FC = () => {
  const [incidentId, setIncidentId] = useState<string>('inc_hdfs_001');
  const [graphData, setGraphData] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const res = await apiService.fetchEvidenceGraph(incidentId);
      setGraphData(res);
      if (res.nodes?.length > 0) {
        setSelectedNode(res.nodes[0]);
      }
    } catch {
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [incidentId]);

  return (
    <div className="page-container" data-testid="evidence-graph-page">
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="page-title" style={{ margin: 0 }}>Evidence Graph & Provenance DAG</h1>
            <span className="badge badge-neutral" style={{ fontSize: '11px', border: '1px solid #333' }}>
              Dual-Hash Verification
            </span>
          </div>
          <p className="page-subtitle" style={{ margin: '4px 0 0 0' }}>
            Cryptographically inspectable trace connecting incidents to retrieved chunks, claims, citations, and source logs.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#888' }}>Incident:</span>
          <select
            value={incidentId}
            onChange={(e) => setIncidentId(e.target.value)}
            style={{
              background: '#141414',
              color: '#FFF',
              border: '1px solid #333',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '12px',
            }}
          >
            <option value="inc_hdfs_001">HDFS Outage (Timeout / blk_78129)</option>
            <option value="inc_hdfs_002">HDFS Replica Desync (blk_49102)</option>
          </select>
        </div>
      </div>

      {loading && (
        <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
          Generating provenance DAG topology...
        </div>
      )}

      {!loading && graphData && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
          {/* Left: Interactive DAG Node Flow */}
          <div className="card" style={{ padding: '20px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                DAG Flow Topology ({graphData.node_count} Nodes, {graphData.edge_count} Edges)
              </div>
              <span className="badge badge-success" style={{ fontSize: '11px' }}>
                {graphData.integrity}
              </span>
            </div>

            {/* Linear DAG Visualizer */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {graphData.nodes?.map((node: any, idx: number) => {
                const isSelected = selectedNode?.id === node.id;
                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      background: isSelected ? '#1A1A1A' : '#101010',
                      border: `1px solid ${isSelected ? '#FFFFFF' : '#222'}`,
                      borderRadius: '6px',
                      padding: '12px 16px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div
                        style={{
                          width: '26px',
                          height: '26px',
                          borderRadius: '50%',
                          background: isSelected ? '#FFF' : '#222',
                          color: isSelected ? '#000' : '#FFF',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '11px',
                          fontWeight: 700,
                          fontFamily: 'monospace',
                        }}
                      >
                        {idx + 1}
                      </div>

                      <div>
                        <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#888', letterSpacing: '0.05em' }}>
                          {node.type}
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#FFF' }}>
                          {node.label}
                        </div>
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
                        {node.status}
                      </span>
                      <div style={{ fontSize: '10px', fontFamily: 'monospace', color: '#666', marginTop: '4px' }}>
                        hash: {node.hash}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: Selected Node Inspector */}
          {selectedNode && (
            <div className="card" style={{ padding: '20px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#777', letterSpacing: '0.05em' }}>
                Node Inspector
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFF', margin: '4px 0 12px 0' }}>
                {selectedNode.label}
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
                <div style={{ borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <div style={{ color: '#777', fontSize: '11px' }}>Node ID</div>
                  <div style={{ fontFamily: 'monospace', color: '#FFF', wordBreak: 'break-all' }}>{selectedNode.id}</div>
                </div>

                <div style={{ borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <div style={{ color: '#777', fontSize: '11px' }}>Node Type</div>
                  <div style={{ color: '#FFF' }}>{selectedNode.type}</div>
                </div>

                <div style={{ borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <div style={{ color: '#777', fontSize: '11px' }}>Source Component</div>
                  <div style={{ color: '#BBB' }}>{selectedNode.source}</div>
                </div>

                <div style={{ borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <div style={{ color: '#777', fontSize: '11px' }}>Cryptographic Hash</div>
                  <div style={{ fontFamily: 'monospace', color: '#22C55E' }}>{selectedNode.hash}</div>
                </div>

                <div style={{ borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <div style={{ color: '#777', fontSize: '11px' }}>Verification Status</div>
                  <div style={{ color: '#FFF' }}>{selectedNode.status}</div>
                </div>

                {/* Extra Data Attributes */}
                <div style={{ marginTop: '8px' }}>
                  <div style={{ color: '#777', fontSize: '11px', marginBottom: '4px' }}>Extended Node Metadata</div>
                  <pre
                    style={{
                      background: '#050505',
                      border: '1px solid #1E1E1E',
                      borderRadius: '4px',
                      padding: '8px',
                      fontSize: '11px',
                      color: '#D4D4D8',
                      fontFamily: 'monospace',
                      maxHeight: '220px',
                      overflowY: 'auto',
                      margin: 0,
                    }}
                  >
                    {JSON.stringify(selectedNode.data, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
