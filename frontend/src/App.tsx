/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Shell } from './components/layout/Shell';
import { PlayerFooter } from './components/audio/PlayerFooter';
import { LoadingScreen } from './components/layout/LoadingScreen';
import { GantasmoOrb } from './orb-kit/react/GantasmoOrb';
import { AssistantPanel } from './orb-kit/AssistantPanel';
import { logInfo } from './state/logStore';
import { handleStableDAWAction } from './orb-kit/actionHandlers';
import { useStatusBarStore } from './state/statusBarStore';

import './orb-kit/styles/gantasmo-orb.css';
import './orb-kit/chat/orb-chat.css';

export default function App() {
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [orbPosition, setOrbPosition] = useState(() => ({
    x: typeof window !== 'undefined' ? window.innerWidth - 80 : 900,
    y: 500,
  }));
  const [skipped, setSkipped] = useState(false);
  const [minWaitOver, setMinWaitOver] = useState(false);

  const isBackendReady = useStatusBarStore((s) => s.isBackendReady);
  const refreshHealth  = useStatusBarStore((s) => s.refreshHealth);

  // Enforce a minimum 7-second loading screen
  useEffect(() => {
    const t = setTimeout(() => setMinWaitOver(true), 7000);
    return () => clearTimeout(t);
  }, []);

  // Health polling lives here so it runs during the loading screen.
  // Exponential backoff: 1s → 2s → 4s → 8s → 16s until ready, then 30s steady.
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let retryDelay = 1000;

    const poll = async () => {
      if (cancelled) return;
      await refreshHealth();
      if (cancelled) return;
      const ready = useStatusBarStore.getState().isBackendReady;
      retryDelay = ready ? 30000 : Math.min(retryDelay * 2, 16000);
      timer = setTimeout(() => void poll(), retryDelay);
    };

    void poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [refreshHealth]);

  useEffect(() => {
    logInfo('system', 'StableDAW UI initialized');
  }, []);

  const handleAssistantAction = useCallback((action: { type: string; payload?: any }) => {
    const result = handleStableDAWAction(action);
    logInfo('assistant', `Action: ${action.type} → ${result}`);
  }, []);

  const showLoading = (!isBackendReady || !minWaitOver) && !skipped;

  return (
    <>
      {/* Main app always mounts so state initializes, but polls are gated on isBackendReady */}
      <Shell />
      <PlayerFooter />
      <GantasmoOrb
        isActive={isAssistantOpen}
        onToggle={() => setIsAssistantOpen(prev => !prev)}
        onPositionChange={setOrbPosition}
      />
      <AssistantPanel
        isOpen={isAssistantOpen}
        onClose={() => setIsAssistantOpen(false)}
        onExecuteAction={handleAssistantAction}
        orbPosition={orbPosition}
      />

      {/* Loading screen overlays everything until backend is ready */}
      <AnimatePresence>
        {showLoading && (
          <motion.div
            key="loading"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="fixed inset-0 z-200"
          >
            <LoadingScreen onSkip={() => setSkipped(true)} />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
