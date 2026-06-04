import { create } from 'zustand';
import type { PredictionResult } from '../api/client';

interface PileState {
  selectedPileNo: string | null;
  currentPrediction: PredictionResult | null;
  detailDrawerOpen: boolean;
  setSelectedPile: (pileNo: string | null) => void;
  setPrediction: (result: PredictionResult | null) => void;
  openDetailDrawer: () => void;
  closeDetailDrawer: () => void;
}

export const usePileStore = create<PileState>((set) => ({
  selectedPileNo: null,
  currentPrediction: null,
  detailDrawerOpen: false,
  setSelectedPile: (pileNo) => set({ selectedPileNo: pileNo }),
  setPrediction: (result) => set({ currentPrediction: result }),
  openDetailDrawer: () => set({ detailDrawerOpen: true }),
  closeDetailDrawer: () => set({ detailDrawerOpen: false }),
}));
