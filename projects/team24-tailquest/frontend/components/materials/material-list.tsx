"use client";

import { MaterialCard } from "@/components/materials/material-card";
import type { MaterialResponse } from "@/lib/api";

interface Props {
  items: MaterialResponse[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
}

export function MaterialList({ items, selectedIds, onToggle, onDelete }: Props) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-xxl text-center">
        <span className="material-symbols-outlined text-muted mb-md" style={{ fontSize: 40 }}>
          folder_open
        </span>
        <p className="text-body-sm text-muted max-w-xs">
          아직 등록된 자료가 없어요. 위에서 첫 자료를 업로드해 보세요.
        </p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-sm">
      {items.map((item) => (
        <MaterialCard
          key={item.id}
          item={item}
          selected={selectedIds.has(item.id)}
          onToggle={onToggle}
          onDelete={onDelete}
        />
      ))}
    </ul>
  );
}
