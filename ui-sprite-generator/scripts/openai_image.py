#!/usr/bin/env python3
"""Call an OpenAI-compatible image generation or edit endpoint safely."""

import argparse
import base64
import mimetypes
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from data_io import DataIOError, load_data  # noqa: E402


class ImageAPIError(Exception):
    pass


DEFAULT_SUPPORTED_SIZES = ["1536x1024", "1024x1536", "1024x1024"]


def load_env_file(path):
    values = {}
    if not path:
        return values
    env_path = Path(path)
    if not env_path.exists():
        raise ImageAPIError(f"env file not found: {env_path}")
    for line_no, raw in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ImageAPIError(f"invalid env line {line_no}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def merge_env_files(paths):
    values = {}
    for path in paths:
        if not Path(path).exists():
            continue
        values.update(load_env_file(path))
    return values


def env_paths_for_run_dir(run_dir):
    if not run_dir:
        return []
    path = Path(run_dir)
    return [path.parent / ".env", path / ".env"]


def load_env_values(args):
    if args.env_file:
        return load_env_file(args.env_file)
    return merge_env_files(env_paths_for_run_dir(args.run_dir))


def config_value(name, env_values, default=None):
    return os.environ.get(name) or env_values.get(name) or default


def resolve_base_url(args, env_values):
    return args.base_url or config_value("IMAGE_API_BASE_URL", env_values)


def read_prompt(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ImageAPIError(f"prompt file not found: {path}") from exc


def load_spec(path):
    if not path:
        return None
    try:
        return load_data(path)
    except DataIOError as exc:
        raise ImageAPIError(str(exc)) from exc


def source_dimensions(spec):
    try:
        source = spec["source_image"]
        width = int(source["width"])
        height = int(source["height"])
    except (TypeError, KeyError, ValueError) as exc:
        raise ImageAPIError("spec.source_image.width and height are required for auto sizing") from exc
    if width <= 0 or height <= 0:
        raise ImageAPIError("spec.source_image.width and height must be > 0")
    return width, height


def parse_size(size):
    try:
        width_text, height_text = size.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except (AttributeError, ValueError) as exc:
        raise ImageAPIError(f"invalid image size: {size}") from exc
    if width <= 0 or height <= 0:
        raise ImageAPIError(f"invalid image size: {size}")
    return width, height


def cover_crop_area_ratio(candidate_width, candidate_height, target_width, target_height):
    candidate_aspect = candidate_width / candidate_height
    target_aspect = target_width / target_height
    if candidate_aspect > target_aspect:
        kept_width = candidate_height * target_aspect
        kept_height = candidate_height
    else:
        kept_width = candidate_width
        kept_height = candidate_width / target_aspect
    return (candidate_width * candidate_height) / (kept_width * kept_height)


def choose_background_size(spec, supported_sizes=None):
    source_width, source_height = source_dimensions(spec)
    supported = supported_sizes or DEFAULT_SUPPORTED_SIZES
    return min(
        supported,
        key=lambda size: cover_crop_area_ratio(*parse_size(size), source_width, source_height),
    )


def choose_atlas_size(_spec=None):
    return "1536x1024"


def normalize_background_to_source(path, spec):
    target_width, target_height = source_dimensions(spec)
    image_path = Path(path)
    with Image.open(image_path) as image:
        image = image.convert("RGBA")
        source_width, source_height = image.size
        source_aspect = source_width / source_height
        target_aspect = target_width / target_height
        if source_aspect > target_aspect:
            crop_width = round(source_height * target_aspect)
            crop_height = source_height
            left = round((source_width - crop_width) / 2)
            top = 0
        else:
            crop_width = source_width
            crop_height = round(source_width / target_aspect)
            left = 0
            top = round((source_height - crop_height) / 2)
        cropped = image.crop((left, top, left + crop_width, top + crop_height))
        resized = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
        resized.save(path)


def image_to_data_url(path):
    if not path:
        return None
    image_path = Path(path)
    if not image_path.exists():
        raise ImageAPIError(f"input image not found: {image_path}")
    suffix = image_path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def resolve_model(args, env_values):
    return args.model or config_value("IMAGE_API_MODEL", env_values)


def resolve_size(args, env_values, spec=None):
    size = args.size or config_value("IMAGE_API_SIZE", env_values, "1536x1024")
    if size != "auto":
        return size
    if args.purpose == "atlas":
        return choose_atlas_size(spec)
    if args.purpose == "background":
        if spec is None:
            raise ImageAPIError("--spec is required when --size auto is used for background")
        return choose_background_size(spec)
    return "1536x1024"


def resolve_quality(args, env_values):
    return args.quality or config_value("IMAGE_API_QUALITY", env_values)


def resolve_response_format(args, env_values):
    return args.response_format or config_value("IMAGE_API_RESPONSE_FORMAT", env_values)


def build_json_payload(args, env_values, spec=None):
    prompt = read_prompt(args.prompt_file)
    model = resolve_model(args, env_values)
    quality = resolve_quality(args, env_values)
    response_format = resolve_response_format(args, env_values)

    payload = {
        "prompt": prompt,
        "size": resolve_size(args, env_values, spec=spec),
        "n": args.n,
    }
    if model:
        payload["model"] = model
    if quality:
        payload["quality"] = quality
    if response_format:
        payload["response_format"] = response_format
    return payload


def iter_multipart_field(name, value, boundary):
    yield f"--{boundary}\r\n".encode("utf-8")
    yield f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
    yield str(value).encode("utf-8")
    yield b"\r\n"


def iter_multipart_file(name, path, boundary):
    image_path = Path(path)
    if not image_path.exists():
        raise ImageAPIError(f"input image not found: {image_path}")
    mime = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    yield f"--{boundary}\r\n".encode("utf-8")
    yield (
        f'Content-Disposition: form-data; name="{name}"; filename="{image_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    yield image_path.read_bytes()
    yield b"\r\n"


def build_multipart_body(args, env_values, spec=None, boundary=None):
    boundary = boundary or f"----ui-sprite-generator-{os.urandom(12).hex()}"
    model = resolve_model(args, env_values)
    quality = resolve_quality(args, env_values)
    response_format = resolve_response_format(args, env_values)
    fields = {
        "prompt": read_prompt(args.prompt_file),
        "size": resolve_size(args, env_values, spec=spec),
        "n": args.n,
    }
    if model:
        fields["model"] = model
    if quality:
        fields["quality"] = quality
    if response_format:
        fields["response_format"] = response_format

    body_parts = []
    for name, value in fields.items():
        body_parts.extend(iter_multipart_field(name, value, boundary))
    for image in args.input_image or []:
        body_parts.extend(iter_multipart_file("image", image, boundary))
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(body_parts), f"multipart/form-data; boundary={boundary}"


def resolve_mode(args, base_url):
    if args.mode != "auto":
        return args.mode
    if args.input_image or "/edits" in base_url.rstrip("/").lower():
        return "edits"
    return "generations"


def extract_image_bytes(response_body):
    try:
        data = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise ImageAPIError("image API returned non-JSON response") from exc

    items = data.get("data")
    if not isinstance(items, list) or not items:
        raise ImageAPIError("image API response has no data[0]")

    first = items[0]
    if "b64_json" in first:
        try:
            return base64.b64decode(first["b64_json"])
        except (TypeError, ValueError) as exc:
            raise ImageAPIError("image API returned invalid b64_json") from exc

    if "url" in first:
        try:
            with urllib.request.urlopen(first["url"], timeout=60) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ImageAPIError("failed to download image URL from response") from exc

    raise ImageAPIError("image API response must include data[0].b64_json or data[0].url")


def call_api(base_url, api_key, body, content_type, timeout):
    request = urllib.request.Request(
        base_url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise ImageAPIError(f"image API HTTP error: response status {exc.code}; {detail}") from exc
    except TimeoutError as exc:
        raise ImageAPIError(f"image API timeout after {timeout}s") from exc
    except urllib.error.URLError as exc:
        raise ImageAPIError(f"image API request failed: {exc.reason}") from exc


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Call an OpenAI-compatible image generation/edit endpoint using IMAGE_API_* environment variables."
    )
    parser.add_argument("--env-file", type=Path, help="Explicit .env file with IMAGE_API_* values")
    parser.add_argument("--run-dir", type=Path, help="Invocation run directory; reads ../.env then .env when --env-file is omitted")
    parser.add_argument("--base-url", help="Override IMAGE_API_BASE_URL; safe for non-secret endpoint values")
    parser.add_argument("--mode", choices=["auto", "generations", "edits"], default="auto")
    parser.add_argument("--prompt-file", required=True, type=Path, help="Prompt text file")
    parser.add_argument("--output", required=True, type=Path, help="Output image path")
    parser.add_argument("--spec", type=Path, help="spec.yaml or spec.json used for runtime auto sizing and background normalization")
    parser.add_argument("--purpose", choices=["generic", "background", "atlas"], default="generic")
    parser.add_argument(
        "--input-image",
        action="append",
        type=Path,
        help="Reference/source image for edits; repeat for multiple images",
    )
    parser.add_argument("--model", help="Override IMAGE_API_MODEL")
    parser.add_argument("--size", help="Override IMAGE_API_SIZE, e.g. 1536x1024 or auto")
    parser.add_argument("--quality", help="Override IMAGE_API_QUALITY, e.g. high")
    parser.add_argument("--response-format", dest="response_format", help="Override IMAGE_API_RESPONSE_FORMAT")
    parser.add_argument("--n", type=int, default=1, help="Number of images to request; only first image is saved")
    parser.add_argument("--timeout", type=int, help="Override IMAGE_API_TIMEOUT seconds")
    parser.add_argument(
        "--normalize-background-to-source",
        action="store_true",
        help="After background generation, cover-crop and resize output to spec.source_image dimensions",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        env_values = load_env_values(args)
        spec = load_spec(args.spec)
        base_url = resolve_base_url(args, env_values)
        api_key = config_value("IMAGE_API_KEY", env_values)
        timeout = int(args.timeout or config_value("IMAGE_API_TIMEOUT", env_values, "180"))

        if not base_url:
            raise ImageAPIError("IMAGE_API_BASE_URL is required in the environment or --env-file")
        if not api_key:
            raise ImageAPIError("IMAGE_API_KEY is required in the environment or --env-file")
        if timeout <= 0:
            raise ImageAPIError("timeout must be > 0")

        mode = resolve_mode(args, base_url)
        if mode == "edits":
            if not args.input_image:
                raise ImageAPIError("edits mode requires at least one --input-image")
            body, content_type = build_multipart_body(args, env_values, spec=spec)
        else:
            if args.input_image:
                raise ImageAPIError("generations mode does not accept --input-image; use --mode edits")
            body = json.dumps(build_json_payload(args, env_values, spec=spec)).encode("utf-8")
            content_type = "application/json"

        response_body = call_api(base_url, api_key, body, content_type, timeout)
        image_bytes = extract_image_bytes(response_body)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(image_bytes)
        if args.normalize_background_to_source:
            if args.purpose != "background":
                raise ImageAPIError("--normalize-background-to-source requires --purpose background")
            if spec is None:
                raise ImageAPIError("--normalize-background-to-source requires --spec")
            normalize_background_to_source(args.output, spec)
        print(f"Image request: purpose={args.purpose}; size={resolve_size(args, env_values, spec=spec)}")
        print(f"Saved image: {args.output}")
    except ImageAPIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
