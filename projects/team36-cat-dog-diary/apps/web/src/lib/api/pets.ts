import type {
  CreatePetRequest,
  Pet,
  UpdatePetRequest,
} from "@cat-dog-diary/shared-types";

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function createPet(input: CreatePetRequest): Promise<Pet> {
  const res = await fetch("/api/pets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return unwrap<Pet>(res);
}

export async function updatePet(
  id: string,
  input: UpdatePetRequest,
): Promise<Pet> {
  const res = await fetch(`/api/pets/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return unwrap<Pet>(res);
}

export async function deletePet(id: string): Promise<void> {
  const res = await fetch(`/api/pets/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
}
