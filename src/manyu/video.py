from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - environment guard
    raise RuntimeError("Video export requires Pillow. Install the 'Pillow' package to use this command.") from exc


DEFAULT_EMOTIONS = ["fear", "anger", "joy", "trust"]
COLORS = {
    "fear": "#7357b8",
    "anger": "#b24747",
    "joy": "#d49117",
    "sadness": "#2f6fbd",
    "trust": "#2f8f5b",
    "distrust": "#4d5b6d",
    "surprise": "#248997",
    "interest": "#b5527b",
}


def export_emotion_animation(
    timeline_path: str | Path,
    out_path: str | Path,
    emotions: list[str] | None = None,
    fps: int = 12,
    seconds_per_turn: float = 0.75,
    width: int = 1280,
    height: int = 720,
) -> dict[str, Any]:
    timeline = json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    turns = list(timeline.get("turns") or [])
    if not turns:
        raise ValueError("Timeline has no turns to animate.")

    available = list(timeline.get("emotions") or [])
    selected = [emotion for emotion in (emotions or DEFAULT_EMOTIONS) if not available or emotion in available]
    if not selected:
        selected = available[:4] or DEFAULT_EMOTIONS

    frames = _build_frames(timeline, turns, selected, fps, seconds_per_turn, width, height)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = max(20, round(1000 / fps))
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
        disposal=2,
    )
    return {
        "status": "written",
        "path": str(out),
        "format": "gif",
        "frames": len(frames),
        "fps": fps,
        "seconds": round(len(frames) / fps, 2),
        "turns": len(turns),
        "emotions": selected,
    }


def _build_frames(
    timeline: dict[str, Any],
    turns: list[dict[str, Any]],
    emotions: list[str],
    fps: int,
    seconds_per_turn: float,
    width: int,
    height: int,
) -> list[Image.Image]:
    frames_per_turn = max(2, round(fps * seconds_per_turn))
    total_frames = (len(turns) - 1) * frames_per_turn + fps
    frames: list[Image.Image] = []
    for frame_index in range(total_frames):
        progress = min(len(turns) - 1, frame_index / frames_per_turn)
        frames.append(_draw_frame(timeline, turns, emotions, width, height, progress))
    return frames


def _draw_frame(
    timeline: dict[str, Any],
    turns: list[dict[str, Any]],
    emotions: list[str],
    width: int,
    height: int,
    progress: float,
) -> Image.Image:
    image = Image.new("RGB", (width, height), "#f6f7f9")
    draw = ImageDraw.Draw(image)
    font = _fonts()
    draw.rectangle((0, 0, width, height), fill="#ffffff")
    draw.text((42, 26), "Manyu Emotion Trajectory", fill="#172033", font=font["title"])
    source = str(timeline.get("source") or "timeline")
    draw.text((42, 62), source, fill="#657085", font=font["body"])

    plot = (72, 116, width - 54, height - 150)
    _draw_grid(draw, plot, font)
    _draw_turn_axis(draw, turns, plot, progress, font)
    _draw_series(draw, turns, emotions, plot, progress)
    _draw_legend(draw, emotions, width, font)
    _draw_turn_card(draw, turns, progress, width, height, font)
    return image


def _draw_grid(draw: ImageDraw.ImageDraw, plot: tuple[int, int, int, int], font: dict[str, ImageFont.ImageFont]) -> None:
    left, top, right, bottom = plot
    draw.rectangle(plot, outline="#bfc7d3", width=2, fill="#fbfcfe")
    for value in [0, 0.25, 0.5, 0.75, 1]:
        y = _y_for(value, plot)
        draw.line((left, y, right, y), fill="#e1e5ec", width=1)
        draw.text((16, y - 9), f"{value:.2f}", fill="#657085", font=font["small"])
    draw.text((left, bottom + 42), "turns", fill="#657085", font=font["small"])


def _draw_turn_axis(
    draw: ImageDraw.ImageDraw,
    turns: list[dict[str, Any]],
    plot: tuple[int, int, int, int],
    progress: float,
    font: dict[str, ImageFont.ImageFont],
) -> None:
    left, top, _right, bottom = plot
    current_idx = min(len(turns) - 1, int(math.floor(progress)))
    for idx, turn in enumerate(turns):
        x = _x_for(idx, len(turns), plot)
        active = idx == current_idx
        draw.line((x, top, x, bottom), fill="#172033" if active else "#c9d0dc", width=3 if active else 1)
        label = f"T{turn.get('index', idx + 1)}"
        bbox = draw.textbbox((0, 0), label, font=font["small"])
        draw.text((x - (bbox[2] - bbox[0]) / 2, bottom + 16), label, fill="#172033" if active else "#657085", font=font["small"])
    if len(turns) == 1:
        draw.text((left, bottom + 16), "T1", fill="#172033", font=font["small"])


def _draw_series(
    draw: ImageDraw.ImageDraw,
    turns: list[dict[str, Any]],
    emotions: list[str],
    plot: tuple[int, int, int, int],
    progress: float,
) -> None:
    for emotion in emotions:
        color = COLORS.get(emotion, "#333333")
        points = _state_points(turns, emotion, plot, progress, "post_state")
        if len(points) > 1:
            draw.line(points, fill=color, width=4, joint="curve")
        for point in points[:-1]:
            _circle(draw, point, 5, color, color)
        if points:
            _circle(draw, points[-1], 8, color, color)

    for emotion in emotions:
        color = COLORS.get(emotion, "#333333")
        segments = _perceived_segments(turns, emotion, plot, progress)
        for segment in segments:
            if len(segment) > 1:
                _dashed_line(draw, segment, color, width=3)
            for point in segment:
                _circle(draw, point, 6, "#ffffff", color)


def _draw_legend(draw: ImageDraw.ImageDraw, emotions: list[str], width: int, font: dict[str, ImageFont.ImageFont]) -> None:
    x = width - 440
    y = 34
    for emotion in emotions:
        color = COLORS.get(emotion, "#333333")
        draw.line((x, y + 8, x + 34, y + 8), fill=color, width=4)
        draw.text((x + 44, y), emotion, fill="#172033", font=font["body"])
        x += 104
    draw.line((width - 440, y + 42, width - 406, y + 42), fill="#2f6fbd", width=4)
    draw.text((width - 394, y + 32), "actual", fill="#657085", font=font["small"])
    _dashed_line(draw, [(width - 318, y + 42), (width - 284, y + 42)], "#2f6fbd", width=3)
    draw.text((width - 272, y + 32), "partial perceived", fill="#657085", font=font["small"])


def _draw_turn_card(
    draw: ImageDraw.ImageDraw,
    turns: list[dict[str, Any]],
    progress: float,
    width: int,
    height: int,
    font: dict[str, ImageFont.ImageFont],
) -> None:
    idx = min(len(turns) - 1, int(math.floor(progress)))
    turn = turns[idx]
    top = height - 116
    draw.rectangle((42, top, width - 42, height - 34), fill="#ffffff", outline="#d8dde6", width=2)
    title = f"Turn {turn.get('index', idx + 1)}: {turn.get('event_type', 'event')}"
    draw.text((64, top + 18), title, fill="#172033", font=font["subtitle"])
    disposition = (turn.get("arbitration") or {}).get("disposition", "")
    if disposition:
        draw.text((width - 250, top + 20), disposition, fill="#172033", font=font["body"])
    summary = _ellipsize(str(turn.get("summary") or ""), 128)
    draw.text((64, top + 50), summary, fill="#657085", font=font["body"])


def _state_points(
    turns: list[dict[str, Any]],
    emotion: str,
    plot: tuple[int, int, int, int],
    progress: float,
    field: str,
) -> list[tuple[int, int]]:
    max_idx = min(len(turns) - 1, int(math.floor(progress)))
    points = [
        (_x_for(idx, len(turns), plot), _y_for(_value(turns[idx], field, emotion), plot))
        for idx in range(max_idx + 1)
    ]
    if max_idx < len(turns) - 1 and progress > max_idx:
        t = progress - max_idx
        value = _lerp(_value(turns[max_idx], field, emotion), _value(turns[max_idx + 1], field, emotion), t)
        x = round(_lerp(_x_for(max_idx, len(turns), plot), _x_for(max_idx + 1, len(turns), plot), t))
        points.append((x, _y_for(value, plot)))
    return points


def _perceived_segments(
    turns: list[dict[str, Any]],
    emotion: str,
    plot: tuple[int, int, int, int],
    progress: float,
) -> list[list[tuple[int, int]]]:
    raw = _state_points(turns, emotion, plot, progress, "perceived_affects")
    segments: list[list[tuple[int, int]]] = []
    current: list[tuple[int, int]] = []
    max_idx = min(len(turns) - 1, math.ceil(progress))
    for idx in range(max_idx + 1):
        if (turns[idx].get("perceived_affects") or {}).get(emotion) is None:
            if current:
                segments.append(current)
            current = []
            continue
        if idx < len(raw):
            current.append(raw[idx])
    if current:
        segments.append(current)
    return segments


def _value(turn: dict[str, Any], field: str, emotion: str) -> float:
    return _clamp((turn.get(field) or {}).get(emotion, 0))


def _x_for(index: int, count: int, plot: tuple[int, int, int, int]) -> int:
    left, _top, right, _bottom = plot
    if count <= 1:
        return round((left + right) / 2)
    return round(left + ((right - left) * index / (count - 1)))


def _y_for(value: float, plot: tuple[int, int, int, int]) -> int:
    _left, top, _right, bottom = plot
    return round(top + (1 - _clamp(value)) * (bottom - top))


def _dashed_line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill: str, width: int) -> None:
    for start, end in zip(points, points[1:]):
        _dash_segment(draw, start, end, fill, width)


def _dash_segment(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: str,
    width: int,
    dash: int = 12,
    gap: int = 8,
) -> None:
    x1, y1 = start
    x2, y2 = end
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    distance = 0.0
    while distance < length:
        next_distance = min(length, distance + dash)
        sx = x1 + (x2 - x1) * distance / length
        sy = y1 + (y2 - y1) * distance / length
        ex = x1 + (x2 - x1) * next_distance / length
        ey = y1 + (y2 - y1) * next_distance / length
        draw.line((sx, sy, ex, ey), fill=fill, width=width)
        distance += dash + gap


def _circle(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, fill: str, outline: str) -> None:
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline=outline, width=2)


def _fonts() -> dict[str, ImageFont.ImageFont]:
    candidates = [
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    font_path = next((path for path in candidates if path.exists()), None)
    if not font_path:
        default = ImageFont.load_default()
        return {"title": default, "subtitle": default, "body": default, "small": default}
    return {
        "title": ImageFont.truetype(str(font_path), 34),
        "subtitle": ImageFont.truetype(str(font_path), 22),
        "body": ImageFont.truetype(str(font_path), 18),
        "small": ImageFont.truetype(str(font_path), 15),
    }


def _ellipsize(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def _lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * max(0, min(1, t))


def _clamp(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))
