"use client";

import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Pet } from "@cat-dog-diary/shared-types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createPetSchema, type CreatePetInput } from "@/lib/validators/pet";

type Props = {
  defaultValues?: Pet;
  submitLabel: string;
  onSubmit: (input: CreatePetInput) => Promise<void>;
};

export function PetForm({ defaultValues, submitLabel, onSubmit }: Props) {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<CreatePetInput>({
    resolver: zodResolver(createPetSchema),
    defaultValues: defaultValues
      ? {
          name: defaultValues.name,
          species: defaultValues.species,
          honorific: defaultValues.honorific,
          gender: defaultValues.gender,
        }
      : { gender: "unknown" },
  });

  async function submit(values: CreatePetInput) {
    try {
      await onSubmit(values);
    } catch (e) {
      const message = e instanceof Error ? e.message : "요청 실패";
      setError("root", { message });
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Label htmlFor="name" className="text-base">
          이름{" "}
          <span className="text-muted-foreground text-sm">(1~20자)</span>
        </Label>
        <Input
          id="name"
          placeholder="예: 까망이"
          className="h-12 text-base"
          {...register("name")}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="species" className="text-base">
          종{" "}
          <span className="text-muted-foreground text-sm">
            (고양이/강아지 또는 자유 입력)
          </span>
        </Label>
        <Input
          id="species"
          placeholder="예: 고양이"
          className="h-12 text-base"
          {...register("species")}
        />
        {errors.species && (
          <p className="text-sm text-destructive">{errors.species.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="honorific" className="text-base">
          호칭{" "}
          <span className="text-muted-foreground text-sm">
            (반려동물이 사용자를 부르는 말)
          </span>
        </Label>
        <Input
          id="honorific"
          placeholder="예: 집사, 누나"
          className="h-12 text-base"
          {...register("honorific")}
        />
        {errors.honorific && (
          <p className="text-sm text-destructive">{errors.honorific.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="gender" className="text-base">
          성별
        </Label>
        <Controller
          control={control}
          name="gender"
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger id="gender" className="h-12 w-full text-base">
                <SelectValue placeholder="성별 선택" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="male">수컷</SelectItem>
                <SelectItem value="female">암컷</SelectItem>
                <SelectItem value="unknown">모름</SelectItem>
              </SelectContent>
            </Select>
          )}
        />
        {errors.gender && (
          <p className="text-sm text-destructive">{errors.gender.message}</p>
        )}
      </div>

      {errors.root && (
        <p className="text-sm text-destructive">{errors.root.message}</p>
      )}

      <Button
        type="submit"
        disabled={isSubmitting}
        size="lg"
        className="h-14 rounded-md text-lg font-medium"
      >
        {isSubmitting ? "저장 중..." : submitLabel}
      </Button>
    </form>
  );
}
