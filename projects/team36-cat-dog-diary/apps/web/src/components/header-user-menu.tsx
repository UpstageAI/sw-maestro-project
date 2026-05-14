"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDownIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { EditNicknameDialog } from "@/components/edit-nickname-dialog";

interface HeaderUserMenuProps {
  displayName: string;
  email: string;
}

export function HeaderUserMenu({ displayName, email }: HeaderUserMenuProps) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      const supabase = createSupabaseBrowserClient();
      await supabase.auth.signOut();
      router.replace("/login");
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "로그아웃 실패");
      setSigningOut(false);
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="outline"
              disabled={signingOut}
              className="h-10 px-4 text-base"
            />
          }
        >
          <span className="max-w-40 truncate">{displayName}</span>
          <ChevronDownIcon data-icon="inline-end" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-48">
          <DropdownMenuGroup>
            <DropdownMenuLabel className="truncate">{email}</DropdownMenuLabel>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setEditOpen(true)}>
            닉네임 변경
          </DropdownMenuItem>
          <DropdownMenuItem variant="destructive" onClick={handleSignOut}>
            로그아웃
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <EditNicknameDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        initialName={displayName}
      />
    </>
  );
}
