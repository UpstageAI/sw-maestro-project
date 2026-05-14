"use client";

import { useRouter } from "next/navigation";
import { PetForm } from "@/components/pet-form";
import { createPet } from "@/lib/api/pets";

export function NewPetClient() {
  const router = useRouter();

  return (
    <PetForm
      submitLabel="등록"
      onSubmit={async (input) => {
        await createPet(input);
        router.replace("/");
        router.refresh();
      }}
    />
  );
}
