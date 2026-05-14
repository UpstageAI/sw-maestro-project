"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MoreHorizontalIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DeletePetDialog } from "@/components/delete-pet-dialog";

interface PetRowMenuProps {
  petId: string;
  petName: string;
}

export function PetRowMenu({ petId, petName }: PetRowMenuProps) {
  const router = useRouter();
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="outline"
              size="icon-sm"
              aria-label={`${petName} 메뉴`}
              className="text-muted-foreground"
            />
          }
        >
          <MoreHorizontalIcon />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-32">
          <DropdownMenuItem onClick={() => router.push(`/pets/${petId}/edit`)}>
            수정
          </DropdownMenuItem>
          <DropdownMenuItem
            variant="destructive"
            onClick={() => setDeleteOpen(true)}
          >
            삭제
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <DeletePetDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        petId={petId}
        petName={petName}
      />
    </>
  );
}
