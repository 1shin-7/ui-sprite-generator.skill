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


class ImageAPIError(Exception):
    pass


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


def resolve_size(args, env_values):
    return args.size or config_value("IMAGE_API_SIZE", env_values, "1536x1024")


def resolve_quality(args, env_values):
    return args.quality or config_value("IMAGE_API_QUALITY", env_values)


def resolve_response_format(args, env_values):
    return args.response_format or config_value("IMAGE_API_RESPONSE_FORMAT", env_values)


def build_json_payload(args, env_values):
    prompt = read_prompt(args.prompt_file)
    model = resolve_model(args, env_values)
    quality = resolve_quality(args, env_values)
    response_format = resolve_response_format(args, env_values)

    payload = {
        "prompt": prompt,
        "size": resolve_size(args, env_values),
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


def build_multipart_body(args, env_values, boundary=None):
    boundary = boundary or f"----ui-sprite-generator-{os.urandom(12).hex()}"
    model = resolve_model(args, env_values)
    quality = resolve_quality(args, env_values)
    response_format = resolve_response_format(args, env_values)
    fields = {
        "prompt": read_prompt(args.prompt_file),
        "size": resolve_size(args, env_values),
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
    parser.add_argument(
        "--input-image",
        action="append",
        type=Path,
        help="Reference/source image for edits; repeat for multiple images",
    )
    parser.add_argument("--model", help="Override IMAGE_API_MODEL")
    parser.add_argument("--size", help="Override IMAGE_API_SIZE, e.g. 1536x1024")
    parser.add_argument("--quality", help="Override IMAGE_API_QUALITY, e.g. high")
    parser.add_argument("--response-format", dest="response_format", help="Override IMAGE_API_RESPONSE_FORMAT")
    parser.add_argument("--n", type=int, default=1, help="Number of images to request; only first image is saved")
    parser.add_argument("--timeout", type=int, help="Override IMAGE_API_TIMEOUT seconds")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        env_values = load_env_values(args)
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
            body, content_type = build_multipart_body(args, env_values)
        else:
            if args.input_image:
                raise ImageAPIError("generations mode does not accept --input-image; use --mode edits")
            body = json.dumps(build_json_payload(args, env_values)).encode("utf-8")
            content_type = "application/json"

        response_body = call_api(base_url, api_key, body, content_type, timeout)
        image_bytes = extract_image_bytes(response_body)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(image_bytes)
        print(f"Saved image: {args.output}")
    except ImageAPIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
