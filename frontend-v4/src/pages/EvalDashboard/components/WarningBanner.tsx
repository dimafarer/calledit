/** Displays ground_truth_limitation and bias_warning from run metadata. */

import type { RunMetadata } from '../types';

interface Props {
  metadata: RunMetadata;
}

export default function WarningBanner({ metadata }: Props) {
  const warnings: string[] = [];
  if (metadata.ground_truth_limitation) warnings.push(metadata.ground_truth_limitation);
  if (metadata.bias_warning) warnings.push(metadata.bias_warning);
  if (warnings.length === 0) return null;

  return (
    <div style={{ marginBottom: '1rem' }}>
      {warnings.map((w, i) => (
        <div key={i} style={{
          background: '#78350f', padding: '0.5rem 1rem', borderRadius: 4,
          marginBottom: '0.5rem', color: '#fef3c7', fontSize: '0.85rem',
        }}>
          ⚠ {w}
        </div>
      ))}
    </div>
  );
}
