import { create } from "zustand";

type UiState = {
  sidebarOpen: boolean;
  setSidebarOpen: (value: boolean) => void;
};

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: false,
  setSidebarOpen: (value) => set({ sidebarOpen: value }),
}));
