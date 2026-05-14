import type {
  Profile,
  UpdateProfileRequest,
} from "@cat-dog-diary/shared-types";

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function updateProfile(
  input: UpdateProfileRequest,
): Promise<Profile> {
  const res = await fetch("/api/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return unwrap<Profile>(res);
}
