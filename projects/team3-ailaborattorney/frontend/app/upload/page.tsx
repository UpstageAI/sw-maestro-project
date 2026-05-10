import UploadForm from "@/components/upload-form";

export default function UploadPage() {
  return (
    <section className="space-y-7">
      <div className="space-y-2 pt-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-toss-blue-bg px-2.5 py-1 text-[11px] font-semibold text-toss-blue">
          STEP 1 · 업로드
        </span>
        <h1 className="text-[24px] sm:text-[28px] font-bold tracking-tight text-grey-900 leading-tight">
          계약서를 올려주세요
        </h1>
        <p className="text-[14px] sm:text-[15px] text-grey-600 leading-relaxed">
          PDF나 사진을 올리면 OCR · 룰엔진 · AI가 차례로 검토합니다. 보통 30초면 끝나요.
        </p>
      </div>
      <UploadForm />
    </section>
  );
}
