import React, { useState, useEffect } from 'react';
import {
  FileKey,
  Copy,
  Download,
  RotateCw,
} from 'lucide-react';
import { apiService } from '../services/api';

export const DecisionPassportPage: React.FC = () => {
  const [incidentId] = useState<string>('inc_hdfs_001');
  const [passportData, setPassportData] = useState<any>(null);
  const [markdownReport, setMarkdownReport] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);
  const [verifyStatus, setVerifyStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Human Review State
  const [humanDecision, setHumanDecision] = useState<'CONFIRM' | 'REJECT' | 'NEEDS_REVIEW'>('CONFIRM');
  const [rejectReason, setRejectReason] = useState<string>('False Positive');
  const [reviewerNotes, setReviewerNotes] = useState<string>('');
  const [reviewSubmitted, setReviewSubmitted] = useState<boolean>(false);

  const fetchPassport = async () => {
    setLoading(true);
    try {
      const res = await apiService.fetchDecisionPassport(incidentId);
      setPassportData(res.passport);
      setMarkdownReport(res.markdown_report);
      setVerifyStatus(null);
    } catch {
      setPassportData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPassport();
  }, [incidentId]);

  const handleCopyJson = () => {
    if (!passportData) return;
    navigator.clipboard.writeText(JSON.stringify(passportData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportJson = () => {
    if (!passportData) return;
    const blob = new Blob([JSON.stringify(passportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `passport_${passportData.incident_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportReport = () => {
    if (!markdownReport) return;
    const blob = new Blob([markdownReport], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `passport_${incidentId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleVerify = async () => {
    if (!passportData) return;
    try {
      const res = await apiService.verifyDecisionPassport(incidentId, passportData);
      setVerifyStatus(res.is_valid ? 'SIGNATURE VALID & UN-TAMPERED' : 'SIGNATURE INVALID');
    } catch {
      setVerifyStatus('VERIFICATION FAILED');
    }
  };

  const handleSubmitReview = async () => {
    try {
      await apiService.submitHumanReview(incidentId, {
        human_decision: humanDecision,
        machine_decision: passportData?.final_decision || 'ESCALATE',
        reason: humanDecision === 'REJECT' ? rejectReason : undefined,
        notes: reviewerNotes,
        reviewer_id: 'sre-oncall-lead',
      });
      setReviewSubmitted(true);
      setTimeout(() => setReviewSubmitted(false), 3000);
    } catch (err: any) {
      alert(`Review submission error: ${err.message}`);
    }
  };

  return (
    <div className="page-container" data-testid="decision-passport-page">
      {/* Title Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="page-title" style={{ margin: 0 }}>FAULTSENTINEL DECISION PASSPORT</h1>
            <span className="badge badge-success" style={{ fontSize: '11px', border: '1px solid #14532D' }}>
              Cryptographically Audited
            </span>
          </div>
          <p className="page-subtitle" style={{ margin: '4px 0 0 0' }}>
            Compact, immutable record binding incident triage decisions to conformal bounds and dual-hash provenance.
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={handleCopyJson}>
            <Copy size={13} style={{ marginRight: '4px' }} /> {copied ? 'Copied!' : 'Copy JSON'}
          </button>
          <button className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={handleExportJson}>
            <Download size={13} style={{ marginRight: '4px' }} /> Export JSON
          </button>
          <button className="btn btn-primary" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={handleExportReport}>
            <Download size={13} style={{ marginRight: '4px' }} /> Export Report
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
          Generating tamper-evident audit passport...
        </div>
      )}

      {!loading && passportData && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
          {/* Left: Passport Technical Document */}
          <div className="card" style={{ padding: '24px', background: '#080808', border: '1px solid #222' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #222', paddingBottom: '14px', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileKey size={22} color="#FFF" />
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 700, letterSpacing: '0.05em', color: '#FFF' }}>
                    DECISION PASSPORT — {passportData.incident_id}
                  </div>
                  <div style={{ fontSize: '11px', color: '#666', fontFamily: 'monospace' }}>
                    Commit: {passportData.git_commit} | Pipeline: {passportData.pipeline_version}
                  </div>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span className={`badge ${passportData.status === 'VERIFIED' ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '12px', padding: '4px 10px' }}>
                  {passportData.status}
                </span>
              </div>
            </div>

            {/* Passport Data Grid (23 attributes) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', fontSize: '12px', marginBottom: '20px' }}>
              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Anomaly Score</div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#EF4444', fontFamily: 'monospace', marginTop: '2px' }}>
                  {passportData.anomaly_score}
                </div>
              </div>

              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Conformal Threshold ($\tau_\alpha$)</div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#FFF', fontFamily: 'monospace', marginTop: '2px' }}>
                  {passportData.threshold}
                </div>
              </div>

              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Calibration $\alpha$</div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#FFF', fontFamily: 'monospace', marginTop: '2px' }}>
                  {passportData.calibration_alpha}
                </div>
              </div>

              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Conformal Gate</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFF', marginTop: '2px' }}>
                  {passportData.conformal_decision}
                </div>
              </div>

              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Final Decision</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#22C55E', marginTop: '2px' }}>
                  {passportData.final_decision}
                </div>
              </div>

              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Assigned Severity</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFF', marginTop: '2px' }}>
                  {passportData.severity}
                </div>
              </div>

              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Retrieval / Evidence Count</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFF', marginTop: '2px' }}>
                  {passportData.retrieval_count} chunks ({passportData.mmr_evidence_count} MMR)
                </div>
              </div>

              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Citations Verified</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFF', marginTop: '2px' }}>
                  {passportData.citation_count} Citations
                </div>
              </div>

              <div style={{ background: '#101010', padding: '10px', borderRadius: '4px', border: '1px solid #1C1C1C' }}>
                <div style={{ color: '#777', fontSize: '11px' }}>Faithfulness Status</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#22C55E', marginTop: '2px' }}>
                  {passportData.faithfulness_status}
                </div>
              </div>
            </div>

            {/* Cryptographic Hashes Box */}
            <div style={{ background: '#030303', border: '1px solid #222', borderRadius: '6px', padding: '16px', fontSize: '11px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontWeight: 600, color: '#888', textTransform: 'uppercase' }}>Cryptographic Audit Signatures</span>
                <button className="btn btn-secondary" style={{ fontSize: '10px', padding: '2px 8px' }} onClick={handleVerify}>
                  <RotateCw size={11} style={{ marginRight: '4px' }} /> Verify Signature
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontFamily: 'monospace' }}>
                <div>
                  <span style={{ color: '#666' }}>config_hash: </span>
                  <span style={{ color: '#A1A1AA' }}>{passportData.configuration_hash}</span>
                </div>
                <div>
                  <span style={{ color: '#666' }}>evidence_hash: </span>
                  <span style={{ color: '#A1A1AA' }}>{passportData.evidence_hash}</span>
                </div>
                <div>
                  <span style={{ color: '#666' }}>decision_hash: </span>
                  <span style={{ color: '#22C55E' }}>{passportData.decision_hash}</span>
                </div>
              </div>

              {verifyStatus && (
                <div style={{ marginTop: '10px', padding: '6px 10px', borderRadius: '4px', background: 'rgba(34,197,94,0.1)', color: '#22C55E', fontWeight: 600 }}>
                  {verifyStatus}
                </div>
              )}
            </div>
          </div>

          {/* Right: SRE Human Adjudication Panel */}
          <div className="card" style={{ padding: '20px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#777', letterSpacing: '0.05em', marginBottom: '6px' }}>
              Human Adjudication (Rule 9)
            </div>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#FFF', margin: '0 0 12px 0' }}>
              Record SRE Verification
            </h3>

            <p style={{ fontSize: '11px', color: '#888', lineHeight: 1.4, margin: '0 0 14px 0' }}>
              Adjudication outcomes serve strictly as operational review telemetry. Machine models and frozen benchmarks remain unmodified.
            </p>

            {/* Decision Buttons */}
            <div style={{ display: 'flex', gap: '6px', marginBottom: '14px' }}>
              <button
                className={`btn ${humanDecision === 'CONFIRM' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ flex: 1, fontSize: '11px', padding: '6px 0' }}
                onClick={() => setHumanDecision('CONFIRM')}
              >
                Confirm
              </button>
              <button
                className={`btn ${humanDecision === 'REJECT' ? 'btn-danger' : 'btn-secondary'}`}
                style={{ flex: 1, fontSize: '11px', padding: '6px 0' }}
                onClick={() => setHumanDecision('REJECT')}
              >
                Reject
              </button>
              <button
                className={`btn ${humanDecision === 'NEEDS_REVIEW' ? 'btn-secondary' : 'btn-secondary'}`}
                style={{ flex: 1, fontSize: '11px', padding: '6px 0', border: humanDecision === 'NEEDS_REVIEW' ? '1px solid #F59E0B' : undefined }}
                onClick={() => setHumanDecision('NEEDS_REVIEW')}
              >
                Review
              </button>
            </div>

            {/* Rejection Reason Selector if Reject */}
            {humanDecision === 'REJECT' && (
              <div style={{ marginBottom: '12px' }}>
                <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>
                  Rejection Reason:
                </label>
                <select
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  style={{
                    width: '100%',
                    background: '#141414',
                    color: '#FFF',
                    border: '1px solid #333',
                    borderRadius: '4px',
                    padding: '6px 8px',
                    fontSize: '11px',
                  }}
                >
                  <option value="False Positive">False Positive</option>
                  <option value="Insufficient Evidence">Insufficient Evidence</option>
                  <option value="Wrong Severity">Wrong Severity</option>
                  <option value="Wrong Root Cause">Wrong Root Cause</option>
                  <option value="Missing Evidence">Missing Evidence</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            )}

            {/* Notes */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>
                Engineer Notes:
              </label>
              <textarea
                rows={3}
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="Optional SRE incident notes..."
                style={{
                  width: '100%',
                  background: '#141414',
                  color: '#FFF',
                  border: '1px solid #333',
                  borderRadius: '4px',
                  padding: '6px 8px',
                  fontSize: '11px',
                  resize: 'none',
                }}
              />
            </div>

            <button className="btn btn-primary" style={{ width: '100%', fontSize: '12px' }} onClick={handleSubmitReview}>
              Record Adjudication
            </button>

            {reviewSubmitted && (
              <div style={{ marginTop: '10px', fontSize: '11px', color: '#22C55E', textAlign: 'center' }}>
                ✓ Adjudication recorded to audit trail.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
