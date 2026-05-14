from __future__ import annotations

import argparse
import json

from app.config import get_settings
from app.core.models import JobCreate
from app.services.pipeline import HireProofPipeline


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--job-key", choices=["backend", "frontend", "all"], default="all")
    args = cli.parse_args()

    pipeline = HireProofPipeline()
    base_dir = get_settings().data_dir / "demo_samples"
    manifest = json.loads((base_dir / "scenarios" / "demo_seed_manifest.json").read_text(encoding="utf-8"))

    for job_config in manifest["jobs"]:
        if args.job_key != "all" and job_config["key"] != args.job_key:
            continue
        job_text = (base_dir / job_config["jd_file"]).read_text(encoding="utf-8")
        job = pipeline.create_job(JobCreate(title=job_config["title"], jd_text=job_text))
        pipeline.confirm_criteria(job.id, [criterion.model_dump() for criterion in job.criteria])

        print(f"Seeded demo job: {job_config['key']} -> {job.id}")
        for relative_path in job_config["candidate_files"]:
            file_path = base_dir / relative_path
            pipeline.add_candidate_from_upload(
                job.id,
                candidate_name=file_path.stem,
                filename=file_path.name,
                file_bytes=file_path.read_bytes(),
            )
            print(f"  Seeded candidate: {file_path.name}")


if __name__ == "__main__":
    main()
