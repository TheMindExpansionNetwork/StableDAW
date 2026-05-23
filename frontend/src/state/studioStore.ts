import { create } from 'zustand';
import { useStatusBarStore } from './statusBarStore';
import { logError, logInfo } from './logStore';
import { uuid } from '../orb-kit/utils';
import { useLibraryStore } from './libraryStore';
import { usePlayerStore } from './playerStore';

interface StudioHistoryEntry {
  id: string;
  effect: string;
  format: string;
  createdAt: number;
}

interface StudioStoreState {
  sourceFile: File | null;
  outputUrl: string | null;
  outputFormat: string;
  isProcessing: boolean;
  error: string | null;
  processHistory: StudioHistoryEntry[];
  // Pending action kept in sync by StudioView so GlobalGenerateBar can fire without local state.
  pendingEffect: string;
  pendingParams: Record<string, number>;
  setSourceFile: (file: File | null) => void;
  setOutputFormat: (format: string) => void;
  setPendingAction: (effect: string, params: Record<string, number>) => void;
  processAudio: (payload: { effect: string; params: Record<string, number>; skipLibrary?: boolean }) => Promise<void>;
  triggerPendingProcess: () => Promise<void>;
  reuseOutputAsSource: () => Promise<void>;
  clearOutput: () => void;
}

const parseErrorText = async (response: Response): Promise<string> => {
  try {
    const payload = (await response.json()) as { detail?: string; error?: string };
    return payload.detail || payload.error || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
};

export const useStudioStore = create<StudioStoreState>()((set, get) => ({
  sourceFile: null,
  outputUrl: null,
  outputFormat: 'wav',
  isProcessing: false,
  error: null,
  processHistory: [],
  pendingEffect: 'mastering_chain',
  pendingParams: { lowBoost: 0, highBoost: 0, limiterCeiling: 0.95, targetLUFS: -14 },

  setSourceFile: (file) => {
    set({ sourceFile: file });
    useStatusBarStore.getState().setText(file ? `STUDIO SOURCE LOADED: ${file.name}` : 'STUDIO SOURCE CLEARED');
  },

  setOutputFormat: (format) => {
    set({ outputFormat: format });
  },

  setPendingAction: (effect, params) => {
    set({ pendingEffect: effect, pendingParams: params });
  },

  triggerPendingProcess: async () => {
    const { pendingEffect, pendingParams, processAudio } = get();
    await processAudio({ effect: pendingEffect, params: pendingParams });
  },

  processAudio: async ({ effect, params, skipLibrary }) => {
    const source = get().sourceFile;
    if (!source) {
      const message = 'Load a source audio file before processing.';
      set({ error: message });
      useStatusBarStore.getState().setText(`STUDIO FAILED: ${message}`);
      return;
    }

    const previous = get().outputUrl;
    if (previous) {
      URL.revokeObjectURL(previous);
    }

    set({ isProcessing: true, error: null, outputUrl: null });
    useStatusBarStore.getState().setText(`STUDIO PROCESS STARTED: ${effect}`);
    logInfo('studio', `Processing: effect=${effect} format=${get().outputFormat} source=${source.name} (${Math.round(source.size / 1024)}KB)`);

    const form = new FormData();
    form.append('audio', source);
    form.append('effect', effect);
    form.append('params', JSON.stringify(params));
    form.append('output_format', get().outputFormat);

    try {
      logInfo('studio', `POST /api/studio/process — effect=${effect} params=${JSON.stringify(params)}`);
      const response = await fetch('/api/studio/process', {
        method: 'POST',
        body: form,
      });

      if (!response.ok) {
        const detail = await parseErrorText(response);
        logError('studio', `POST /api/studio/process → ${response.status} ${response.statusText} — ${detail}`);
        throw new Error(detail);
      }

      const blob = await response.blob();
      logInfo('studio', `POST /api/studio/process → 200 OK — ${Math.round(blob.size / 1024)}KB ${get().outputFormat}`);
      const outputUrl = URL.createObjectURL(blob);
      const nextEntry: StudioHistoryEntry = {
        id: uuid(),
        effect,
        format: get().outputFormat,
        createdAt: Date.now(),
      };

      set((state) => ({
        isProcessing: false,
        outputUrl,
        processHistory: [nextEntry, ...state.processHistory].slice(0, 8),
        error: null,
      }));
      useStatusBarStore.getState().setText(`STUDIO PROCESS COMPLETE: ${effect}`);

      if (!skipLibrary) {
        try {
          const entryId = uuid();
          const fmt = get().outputFormat;
          const title = `studio-${effect}.${fmt}`;
          await useLibraryStore.getState().addEntry({
            id: entryId,
            title,
            prompt: `Effect: ${effect}`,
            negativePrompt: '',
            model: effect,
            duration: 0,
            steps: 0,
            cfg: 0,
            seed: 0,
            audioBlob: blob,
            mimeType: blob.type || 'audio/wav',
            timestamp: new Date().toISOString(),
            favorite: false,
            rating: null,
            tags: ['studio', effect],
            notes: '',
            source: 'studio',
          });
          await usePlayerStore.getState().load(blob, { label: title, entryId });
        } catch { /* non-fatal */ }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Studio process failed.';
      set({ isProcessing: false, error: message });
      useStatusBarStore.getState().setText(`STUDIO PROCESS FAILED: ${message}`);
      logError('studio', `effect=${effect} FAILED — ${message}`);
    }
  },

  reuseOutputAsSource: async () => {
    const output = get().outputUrl;
    if (!output) {
      return;
    }

    const response = await fetch(output);
    const blob = await response.blob();
    const sourceFile = new File([blob], `studio-output.${get().outputFormat}`, { type: blob.type || 'audio/wav' });
    set({ sourceFile });
    useStatusBarStore.getState().setText('STUDIO OUTPUT PROMOTED TO SOURCE');
  },

  clearOutput: () => {
    const output = get().outputUrl;
    if (output) {
      URL.revokeObjectURL(output);
    }
    set({ outputUrl: null, error: null });
    useStatusBarStore.getState().setText('STUDIO OUTPUT CLEARED');
  },
}));
