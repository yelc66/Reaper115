import { create } from "zustand";

type Theme = "dark" | "light";

type UiState = {
  sidebarOpen: boolean;
  setSidebarOpen: (value: boolean) => void;
  theme: Theme;
  toggleTheme: () => void;
};

function getStoredTheme(): Theme {
  return localStorage.getItem("theme") === "light" ? "light" : "dark";
}

const storedTheme = getStoredTheme();
document.documentElement.setAttribute("data-theme", storedTheme);

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: false,
  setSidebarOpen: (value) => set({ sidebarOpen: value }),
  theme: storedTheme,
  toggleTheme: () =>
    set((state) => {
      const nextTheme: Theme = state.theme === "dark" ? "light" : "dark";
      localStorage.setItem("theme", nextTheme);
      document.documentElement.setAttribute("data-theme", nextTheme);
      return { theme: nextTheme };
    }),
}));
