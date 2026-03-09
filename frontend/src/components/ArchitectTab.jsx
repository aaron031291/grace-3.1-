import React, { lazy, Suspense } from 'react';
const PlannerPanel = lazy(() => import('./PlannerPanel'));

/**
 * ArchitectTab Stub
 * This component acts as a bridge to the PlannerPanel as part of the architecture/proposer view.
 */
export default function ArchitectTab() {
    return (
        <Suspense fallback={<div style={{ padding: 20, color: '#888' }}>Loading Planner...</div>}>
            <PlannerPanel />
        </Suspense>
    );
}
