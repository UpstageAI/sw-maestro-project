"use client";

import { useId, useRef } from "react";
import { ImagePlus, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Platform, PromotionRequest, Purpose } from "@/lib/types";

const PRODUCT_IMAGE_MAX_BYTES = 6 * 1024 * 1024;
const PRODUCT_IMAGE_ACCEPT = "image/png,image/jpeg,image/webp";
const PRODUCT_IMAGE_ALLOWED_MIMES = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
]);

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error ?? new Error("read error"));
    reader.readAsDataURL(file);
  });
}

const PURPOSE_OPTIONS: { value: Purpose; label: string; helper: string }[] = [
  { value: "new-menu", label: "신메뉴 / 신상품", helper: "오늘 새로 올라온 메뉴 알리기" },
  { value: "event", label: "이벤트 / 할인", helper: "기간 한정 프로모션, 쿠폰" },
  { value: "daily", label: "일상 홍보", helper: "오늘의 한 컷, 단골 인사" },
  { value: "reopening", label: "재오픈 / 리뉴얼", helper: "다시 열어요, 새 단장" },
  { value: "review", label: "단골 후기", helper: "찾아주신 분들 이야기" },
];

const VIBE_PRESETS: { value: string; emoji: string; label: string }[] = [
  { value: "따뜻한", emoji: "🍞", label: "따뜻한" },
  { value: "트렌디한", emoji: "✨", label: "트렌디한" },
  { value: "프리미엄", emoji: "🍷", label: "프리미엄" },
  { value: "발랄한", emoji: "🎈", label: "발랄한" },
  { value: "차분한", emoji: "🌿", label: "차분한" },
];

const PLATFORM_OPTIONS: { value: Platform; label: string }[] = [
  { value: "instagram", label: "인스타그램 (80~150자)" },
  { value: "naver", label: "네이버 플레이스 (200~350자)" },
  { value: "baemin", label: "배달의민족 (120~200자)" },
];

interface StoreFormProps {
  value: PromotionRequest;
  onChange: (next: PromotionRequest) => void;
}

export function StoreForm({ value, onChange }: StoreFormProps) {
  const ids = {
    storeName: useId(),
    category: useId(),
    vibe: useId(),
    description: useId(),
    purpose: useId(),
    detail: useId(),
    platform: useId(),
    productImage: useId(),
  };

  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateStore = <K extends keyof PromotionRequest["store"]>(
    key: K,
    v: PromotionRequest["store"][K],
  ) => onChange({ ...value, store: { ...value.store, [key]: v } });

  const updateRoot = <K extends keyof PromotionRequest>(key: K, v: PromotionRequest[K]) =>
    onChange({ ...value, [key]: v });

  const handlePickProductImage = async (file: File | undefined) => {
    if (!file) return;
    if (!PRODUCT_IMAGE_ALLOWED_MIMES.has(file.type)) {
      toast.error("PNG, JPEG, WebP 파일만 사용할 수 있어요.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    if (file.size > PRODUCT_IMAGE_MAX_BYTES) {
      toast.error("사진은 6MB 이하로 올려주세요.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    try {
      const dataUrl = await readFileAsDataUrl(file);
      updateRoot("productImage", dataUrl);
    } catch {
      toast.error("사진을 읽지 못했어요. 다른 파일로 다시 시도해주세요.");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const clearProductImage = () => {
    updateRoot("productImage", undefined);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="grid gap-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor={ids.storeName}>가게명</Label>
          <Input
            id={ids.storeName}
            value={value.store.storeName}
            onChange={(e) => updateStore("storeName", e.target.value)}
            placeholder="예) 카페 하루의 봄"
            maxLength={40}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor={ids.category}>업종</Label>
          <Input
            id={ids.category}
            value={value.store.category}
            onChange={(e) => updateStore("category", e.target.value)}
            placeholder="예) 브런치 카페"
            maxLength={40}
          />
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor={ids.purpose}>홍보 목적</Label>
          <Select
            value={value.purpose}
            onValueChange={(v) => updateRoot("purpose", v as Purpose)}
          >
            <SelectTrigger id={ids.purpose} className="h-12 w-full">
              <SelectValue placeholder="목적을 선택하세요" />
            </SelectTrigger>
            <SelectContent>
              {PURPOSE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {(() => {
            const cur = PURPOSE_OPTIONS.find((o) => o.value === value.purpose);
            return cur ? (
              <p className="text-xs text-muted-foreground">{cur.helper}</p>
            ) : null;
          })()}
        </div>

        <div className="grid gap-2">
          <Label htmlFor={ids.vibe}>가게 분위기 / 톤</Label>
          <Select
            value={
              VIBE_PRESETS.find((p) => p.value === value.store.vibe)
                ? value.store.vibe
                : VIBE_PRESETS[0].value
            }
            onValueChange={(v) => updateStore("vibe", v)}
          >
            <SelectTrigger id={ids.vibe} className="h-12 w-full">
              <SelectValue placeholder="분위기를 골라주세요" />
            </SelectTrigger>
            <SelectContent>
              {VIBE_PRESETS.map((p) => (
                <SelectItem
                  key={p.value}
                  value={p.value}
                  textValue={`${p.emoji} ${p.label}`}
                >
                  <span className="mr-1.5">{p.emoji}</span>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            카드의 말투와 분위기를 정해요.
          </p>
        </div>
      </div>

      <div className="grid gap-2">
        <Label htmlFor={ids.detail}>홍보 상세 내용</Label>
        <Textarea
          id={ids.detail}
          value={value.detail}
          onChange={(e) => updateRoot("detail", e.target.value)}
          placeholder="예) 새로 출시한 갓 구운 베이글 9,800원, 5월 한정 세트로 어린이날 가족 이벤트 진행"
          maxLength={300}
          rows={4}
        />
        <p className="text-right text-xs text-muted-foreground">
          {value.detail.length}/300
        </p>
      </div>

      <div className="grid gap-2">
        <Label htmlFor={ids.productImage}>제품 사진 (선택)</Label>
        <input
          ref={fileInputRef}
          id={ids.productImage}
          type="file"
          accept={PRODUCT_IMAGE_ACCEPT}
          className="sr-only"
          onChange={(e) => handlePickProductImage(e.target.files?.[0])}
        />
        {value.productImage ? (
          <div className="flex items-center gap-3 rounded-2xl border border-border/70 bg-muted/30 p-3">
            <img
              src={value.productImage}
              alt="제품 사진 미리보기"
              className="size-20 shrink-0 rounded-xl object-cover"
            />
            <div className="flex flex-1 flex-col gap-1">
              <p className="text-sm font-medium">제품 사진을 첨부했어요</p>
              <p className="text-xs text-muted-foreground">
                AI가 이 사진을 참고해 카드 이미지를 만들어요.
              </p>
              <div className="mt-1 flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <ImagePlus className="mr-1 size-3.5" /> 다른 사진
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={clearProductImage}
                >
                  <X className="mr-1 size-3.5" /> 제거
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex flex-col items-center justify-center gap-1 rounded-2xl border border-dashed border-border/80 bg-muted/20 px-4 py-6 text-sm text-muted-foreground transition hover:border-brand-blue-strong hover:bg-brand-blue-soft/30 hover:text-brand-blue-strong"
          >
            <ImagePlus className="size-5" />
            <span className="font-medium">제품 사진 올리기</span>
            <span className="text-xs">PNG / JPG / WebP · 6MB 이하</span>
          </button>
        )}
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor={ids.description}>가게 한 줄 소개 (선택)</Label>
          <Input
            id={ids.description}
            value={value.store.description || ""}
            onChange={(e) => updateStore("description", e.target.value)}
            placeholder="가게의 특징이나 자랑거리"
            maxLength={80}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor={ids.platform}>업로드 플랫폼 (선택)</Label>
          <Select
            value={value.platform ?? "instagram"}
            onValueChange={(v) => updateRoot("platform", v as Platform)}
          >
            <SelectTrigger id={ids.platform} className="h-12 w-full">
              <SelectValue placeholder="플랫폼 선택" />
            </SelectTrigger>
            <SelectContent>
              {PLATFORM_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            플랫폼별 글자수에 맞춰 카피를 작성해요.
          </p>
        </div>
      </div>
    </div>
  );
}
