import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { CategoryId } from "../categories";

type CategoryState = {
  selected: CategoryId[];
  setSelected: (categories: CategoryId[]) => void;
  toggle: (category: CategoryId) => void;
  reset: () => void;
};

const defaultSelectedCategories: CategoryId[] = ["tech"];
const getDefaultSelectedCategories = () => [...defaultSelectedCategories];

export const useCategoryStore = create<CategoryState>()(
  persist(
    (set) => ({
      selected: getDefaultSelectedCategories(),
      setSelected: (categories) => set({ selected: [...categories] }),
      toggle: (category) =>
        set((state) => ({
          selected: state.selected.includes(category)
            ? state.selected.filter((item) => item !== category)
            : [...state.selected, category],
        })),
      reset: () => set({ selected: getDefaultSelectedCategories() }),
    }),
    {
      name: "newspick:selected-categories",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
