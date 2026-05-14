"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Pet } from "@cat-dog-diary/shared-types";
import { Button } from "@/components/ui/button";
import { PetForm } from "@/components/pet-form";
import { deletePet, updatePet } from "@/lib/api/pets";

export function EditPetClient({ pet }: { pet: Pet }) {
  const router = useRouter();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleting(true);
    setDeleteError(null);
    try {
      await deletePet(pet.id);
      router.replace("/");
      router.refresh();
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : "삭제 실패");
      setDeleting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PetForm
        defaultValues={pet}
        submitLabel="저장"
        onSubmit={async (input) => {
          await updatePet(pet.id, input);
          router.replace("/");
          router.refresh();
        }}
      />

      <div className="border-t pt-4">
        {!confirmDelete ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setConfirmDelete(true)}
            className="w-full"
          >
            펫 삭제
          </Button>
        ) : (
          <div className="flex flex-col gap-2">
            <p className="text-sm">
              펫이 메인에서 사라집니다. 일기는 보관됩니다.
            </p>
            <div className="flex gap-2">
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1"
              >
                {deleting ? "삭제 중..." : "삭제 확정"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirmDelete(false)}
                disabled={deleting}
                className="flex-1"
              >
                취소
              </Button>
            </div>
            {deleteError && (
              <p className="text-xs text-destructive">{deleteError}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
