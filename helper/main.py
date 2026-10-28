"""
CLI entrypoint for CloudConvert helper sidecar.
Follows the NDJSON stdout protocol specified in build.md.
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

# Add project root to sys.path so helper modules resolve cleanly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helper.detector import DetectionError, detect_file
from helper.engines.base import EngineError
from helper.registry import Registry
from helper.utils.events import emit_done, emit_error, emit_progress, emit_started
from helper.utils.paths import resolve_output_path, validate_output, OutputValidationError


def cmd_detect_engines() -> int:
    registry = Registry()
    engines = registry.detect_engines()
    print(json.dumps({"event": "engines", "engines": engines}), flush=True)
    return 0


def cmd_detect_file(file_path: str) -> int:
    job = uuid.uuid4().hex[:8]
    try:
        res = detect_file(file_path)
        print(
            json.dumps({
                "event": "file_detected",
                "job": job,
                "format": res.format,
                "valid_targets": list(res.valid_targets),
            }),
            flush=True,
        )
        return 0
    except DetectionError as e:
        emit_error(job=job, code=e.code, message=e.message)
        return 1
    except Exception as e:
        emit_error(job=job, code="CORRUPT_FILE", message=str(e))
        return 1


def cmd_convert(args: argparse.Namespace) -> int:
    job = args.job or uuid.uuid4().hex[:8]
    in_path = Path(args.input_path).resolve()
    target_ext = args.target.lower().lstrip(".")

    try:
        # Step 1: Detect signature and validate file
        emit_progress(job=job, percent=5, stage="Verifying file format...")
        detection = detect_file(str(in_path))

        if target_ext not in detection.valid_targets:
            emit_error(
                job=job,
                code="UNSUPPORTED_TYPE",
                message=f"Cannot convert {detection.format.upper()} to {target_ext.upper()}.",
            )
            return 1

        # Step 2: Resolve non-colliding destination path
        out_path = resolve_output_path(
            input_path=str(in_path),
            target_ext=target_ext,
            out_dir=args.out_dir,
        )

        registry = Registry(preferred_engine=args.preferred_engine)
        pipeline = registry.get_pipeline(detection.format, target_ext)
        first_engine_name = pipeline[0].engine_candidates[0].name if pipeline and pipeline[0].engine_candidates else "unknown"

        emit_started(job=job, engine=first_engine_name)

        def progress_callback(pct: int, stage: str):
            emit_progress(job=job, percent=pct, stage=stage)

    try:
        # Previous conversion steps up to final_out remain unchanged (lines 84-90)
        final_out = registry.execute(
            input_path=in_path,
            output_path=out_path,
            target_ext=target_ext,
            progress_cb=progress_callback,
            pptx_mode=args.pptx_mode,
        )

        # Validate output before signalling success
        try:
            validate_output(final_out, target_ext)
        except OutputValidationError as ve:
            emit_error(job=job, code=ve.code, message=ve.message)
            return 1

        emit_done(job=job, output=str(final_out))
        return 0

    except DetectionError as e:
        emit_error(job=job, code=e.code, message=e.message)
        return 1
    except EngineError as e:
        emit_error(job=job, code=e.code, message=e.message)
        return 1
    except Exception as e:
        emit_error(job=job, code="ENGINE_CRASH", message=f"Unexpected error: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="CloudConvert Helper Sidecar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: detect-engines
    subparsers.add_parser("detect-engines", help="Detect installed converter engines")

    # Subcommand: detect-file
    p_detect = subparsers.add_parser("detect-file", help="Inspect file signature and supported targets")
    p_detect.add_argument("--in", dest="input_path", required=True, help="Input file path")

    # Subcommand: convert
    p_conv = subparsers.add_parser("convert", help="Convert document")
    p_conv.add_argument("--in", dest="input_path", required=True, help="Input file path")
    p_conv.add_argument("--to", dest="target", required=True, help="Target format (pdf, docx, doc, pptx, ppt)")
    p_conv.add_argument("--out-dir", dest="out_dir", default=None, help="Optional output directory")
    p_conv.add_argument("--pptx-mode", dest="pptx_mode", choices=["image", "editable"], default="image")
    p_conv.add_argument("--preferred-engine", dest="preferred_engine", choices=["auto", "office", "libreoffice"], default="auto")
    p_conv.add_argument("--job", dest="job", default=None, help="Job identifier")

    args = parser.parse_args()

    if args.command == "detect-engines":
        return cmd_detect_engines()
    elif args.command == "detect-file":
        return cmd_detect_file(args.input_path)
    elif args.command == "convert":
        return cmd_convert(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
