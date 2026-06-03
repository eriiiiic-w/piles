import { create } from 'zustand';
import type { PredictionResult } from '../api/client';

interface PileState {
  selectedPileNo: string | null;
  currentPrediction: PredictionResult | null;
  setSelectedPile: (pileNo: string | null) => void;
  setPrediction: (result: PredictionResult | null) => void;
}

export const usePileStore = create<PileState>((set) => ({
  selectedPileNo: null,
  currentPrediction: null,
  setSelectedPile: (pileNo) => set({ selectedPileNo: pileNo }),
  setPrediction: (result) => set({ currentPrediction: result }),
}));
