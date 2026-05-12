"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { updateProfile } from "@/lib/api/profile";

interface EditNicknameDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialName: string;
}

export function EditNicknameDialog({
  open,
  onOpenChange,
  initialName,
}: EditNicknameDialogProps) {
  const router = useRouter();
  const [name, setName] = useState(initialName);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed.length < 1 || trimmed.length > 24) {
      toast.error("닉네임은 1~24자여야 해요");
      return;
    }
    if (trimmed === initialName) {
      onOpenChange(false);
      return;
    }
    setSubmitting(true);
    try {
      await updateProfile({ display_name: trimmed });
      toast.success("닉네임을 바꿨어요");
      onOpenChange(false);
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "닉네임 변경 실패");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!submitting) onOpenChange(o);
        if (o) setName(initialName);
      }}
    >
      <DialogContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>닉네임 변경</DialogTitle>
            <DialogDescription>1~24자로 입력해주세요.</DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-2">
            <Label htmlFor="display_name">닉네임</Label>
            <Input
              id="display_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={24}
              autoFocus
              disabled={submitting}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
            >
              취소
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "저장 중..." : "저장"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
