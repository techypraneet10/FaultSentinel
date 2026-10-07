import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  subtext: string;
  context?: string;
  sourceBadge?: {
    text: string;
    type: 'live' | 'benchmark' | 'demo' | 'calibration';
  };
  highlight?: 'normal' | 'success' | 'warning' | 'critical';
  sparkline?: number[];
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subtext,
  context,
  sourceBadge,
  highlight = 'normal',
  sparkline,
}) => {
  const getBadgeStyle = (type: string) => {
    switch (type) {
      case 'live':
        return {
          backgroundColor: '#07190d',
          borderColor: '#144722',
          color: 'var(--color-success)',
        };
      case 'benchmark':
        return {
          backgroundColor: '#111827',
          borderColor: '#374151',
          color: '#e5e7eb',
        };
      case 'calibration':
        return {
          backgroundColor: '#1c1917',
          borderColor: '#44403c',
          color: '#d6d3d1',
        };
      case 'demo':
      default:
        return {
          backgroundColor: '#271b05',
          borderColor: '#573d09',
          color: 'var(--color-warning)',
        };
    }
  };

  const getValueColor = () => {
    switch (highlight) {
      case 'success':
        return 'var(--color-success)';
      case 'warning':
        return 'var(--color-warning)';
      case 'critical':
        return 'var(--color-critical)';
      case 'normal':
      default:
        return 'var(--color-text-pure)';
    }
  };

  return (
    <div
      className="panel"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border-subtle)',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        transition: 'border-color 0.15s ease',
      }}
    >
      <div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: '10px',
          }}
        >
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--color-text-secondary)',
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
            }}
          >
            {label}
          </span>
          {sourceBadge && (
            <span
              className="badge"
              style={{
                fontSize: '9px',
                padding: '1px 5px',
                fontFamily: 'var(--font-mono)',
                borderWidth: '1px',
                borderStyle: 'solid',
                ...getBadgeStyle(sourceBadge.type),
              }}
            >
              {sourceBadge.text}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginBottom: '4px' }}>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '28px',
              fontWeight: 700,
              color: getValueColor(),
              letterSpacing: '-0.5px',
              lineHeight: 1,
            }}
          >
            {value}
          </span>
          {unit && (
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '13px',
                color: 'var(--color-text-muted)',
              }}
            >
              {unit}
            </span>
          )}
        </div>

        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.3 }}>
          {subtext}
        </div>
      </div>

      <div
        style={{
          marginTop: '12px',
          paddingTop: '8px',
          borderTop: '1px solid var(--color-border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '11px',
          color: 'var(--color-text-muted)',
          fontFamily: 'var(--font-mono)',
        }}
      >
        <span>{context || 'Verified telemetry'}</span>
        {sparkline && sparkline.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '14px' }}>
            {sparkline.map((pt, i) => (
              <div
                key={i}
                style={{
                  width: '3px',
                  height: `${Math.max(2, Math.min(14, pt * 14))}px`,
                  backgroundColor: i === sparkline.length - 1 ? 'var(--color-text-pure)' : 'var(--color-border-active)',
                  borderRadius: '1px',
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
