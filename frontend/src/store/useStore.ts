import { create } from "zustand";

export type Theme = "dark" | "light";

interface UserState {
  username: string;
  role: string;
  token: string;
}

interface VajansStore {
  selectedJobId: string | null;
  setSelectedJobId: (id: string | null) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;

  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;

  user: UserState | null;
  setUser: (user: UserState) => void;
  clearUser: () => void;
}

const storedTheme = localStorage.getItem("vajans-theme") as Theme | null;
const storedToken = localStorage.getItem("vajans_token");
const storedUsername = localStorage.getItem("vajans_username");
const storedRole = localStorage.getItem("vajans_role");

export const useStore = create<VajansStore>((set, get) => ({
  selectedJobId: null,
  setSelectedJobId: (id) => set({ selectedJobId: id }),
  activeTab: "overview",
  setActiveTab: (tab) => set({ activeTab: tab }),

  theme: storedTheme ?? "dark",
  setTheme: (theme) => {
    localStorage.setItem("vajans-theme", theme);
    set({ theme });
  },
  toggleTheme: () => {
    const newTheme = get().theme === "dark" ? "light" : "dark";
    localStorage.setItem("vajans-theme", newTheme);
    if (newTheme === "light") {
      document.documentElement.classList.add("light");
      document.documentElement.classList.remove("dark");
    } else {
      document.documentElement.classList.remove("light");
      document.documentElement.classList.add("dark");
    }
    set({ theme: newTheme });
  },

  user:
    storedToken && storedUsername && storedRole
      ? { token: storedToken, username: storedUsername, role: storedRole }
      : null,
  setUser: (user) => {
    localStorage.setItem("vajans_token", user.token);
    localStorage.setItem("vajans_username", user.username);
    localStorage.setItem("vajans_role", user.role);
    set({ user });
  },
  clearUser: () => {
    localStorage.removeItem("vajans_token");
    localStorage.removeItem("vajans_username");
    localStorage.removeItem("vajans_role");
    set({ user: null });
  },
}));
