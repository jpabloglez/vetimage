/**
 * FindingsOverlay — draws AI decision-support finding boxes over the Cornerstone
 * canvas, tracking zoom/pan/window-level by recomputing on every
 * `cornerstoneimagerendered` event via `cornerstone.pixelToCanvas`.
 *
 * Findings carry a normalized `bbox` ([x, y, w, h] in [0,1] image coordinates);
 * only findings with a bbox are drawn. All boxes are explicitly framed as
 * AI decision-support that a veterinarian must confirm — never a diagnosis.
 */
import React, { useEffect, useState } from 'react';
import * as cornerstone from 'cornerstone-core';
import type { Finding } from '../../utils/api';

interface FindingsOverlayProps {
  element: HTMLDivElement | null;
  findings: Finding[];
  visible: boolean;
}

interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
  finding: Finding;
}

export const FindingsOverlay: React.FC<FindingsOverlayProps> = ({ element, findings, visible }) => {
  const [boxes, setBoxes] = useState<Box[]>([]);

  useEffect(() => {
    if (!element || !visible) {
      setBoxes([]);
      return;
    }

    const recompute = () => {
      let enabled: any;
      try {
        enabled = cornerstone.getEnabledElement(element);
      } catch {
        return; // element not enabled yet
      }
      const image = enabled?.image;
      if (!image) {
        setBoxes([]);
        return;
      }
      const iw = image.width;
      const ih = image.height;
      const next: Box[] = [];
      for (const f of findings) {
        const bb = f.bbox;
        if (!bb || bb.length !== 4) continue;
        const [nx, ny, nw, nh] = bb;
        // Map the two image-space corners to canvas space so the box follows
        // the current zoom/pan transform.
        const tl = cornerstone.pixelToCanvas(element, { x: nx * iw, y: ny * ih });
        const br = cornerstone.pixelToCanvas(element, { x: (nx + nw) * iw, y: (ny + nh) * ih });
        next.push({
          left: Math.min(tl.x, br.x),
          top: Math.min(tl.y, br.y),
          width: Math.abs(br.x - tl.x),
          height: Math.abs(br.y - tl.y),
          finding: f,
        });
      }
      setBoxes(next);
    };

    recompute();
    element.addEventListener('cornerstoneimagerendered', recompute);
    window.addEventListener('resize', recompute);
    return () => {
      element.removeEventListener('cornerstoneimagerendered', recompute);
      window.removeEventListener('resize', recompute);
    };
  }, [element, findings, visible]);

  if (!visible || boxes.length === 0) return null;

  return (
    <div className="absolute inset-0 pointer-events-none" data-testid="findings-overlay">
      {boxes.map((b, i) => (
        <div
          key={i}
          className="absolute border-2 border-amber-400/90 rounded-sm shadow-[0_0_0_1px_rgba(0,0,0,0.4)]"
          style={{ left: b.left, top: b.top, width: b.width, height: b.height }}
        >
          <span className="absolute -top-5 left-0 whitespace-nowrap bg-amber-400 text-slate-900 text-[10px] font-semibold px-1 rounded-sm">
            {(b.finding.label ?? 'finding').replace(/_/g, ' ')}
            {b.finding.confidence != null ? ` · ${Math.round(b.finding.confidence * 100)}%` : ''}
          </span>
        </div>
      ))}
    </div>
  );
};

export default FindingsOverlay;
