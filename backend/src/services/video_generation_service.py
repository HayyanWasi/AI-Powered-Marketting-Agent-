import asyncio
import logging
import os
import random
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from supabase import create_client

# Pillow 10+ removed ANTIALIAS; moviepy 1.0.3 still references it
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

# Ensure invalid IMAGEMAGICK_BINARY does not break MoviePy imports (we use Pillow ImageDraw, not TextClip)
if "IMAGEMAGICK_BINARY" in os.environ and not os.path.exists(os.environ["IMAGEMAGICK_BINARY"]):
    os.environ.pop("IMAGEMAGICK_BINARY", None)

from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.fx.all import fadein
from moviepy.video.VideoClip import ImageClip

from src.agents.video_script_agent import VideoScene
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent video renders
_render_semaphore = asyncio.Semaphore(settings.video_max_concurrent_renders)


class VideoGenerationError(Exception):
    pass


class VideoGenerationService:
    def __init__(self):
        self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.bucket = "campaign_assets"

    async def _download_bgm(self, temp_dir: Path) -> Path | None:
        """Download background music."""
        bgm_path = temp_dir / "bgm.mp3"
        url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        logger.info("Downloading BGM...")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
                resp.raise_for_status()
                bgm_path.write_bytes(resp.content)
            return bgm_path
        except Exception as e:
            logger.warning("Failed to download BGM, proceeding without it: %s", e)
            return None

    def _crop_and_resize_to_720_1280(self, filepath: Path):
        """Ensures the image is exactly 720x1280 (720p HD Reel) by center cropping and resizing."""
        try:
            with Image.open(filepath) as img:
                target_ratio = 720 / 1280
                img_ratio = img.width / img.height

                if img_ratio > target_ratio:
                    # Image is too wide, crop left/right
                    new_width = int(target_ratio * img.height)
                    left = (img.width - new_width) / 2
                    img = img.crop((left, 0, left + new_width, img.height))
                elif img_ratio < target_ratio:
                    # Image is too tall, crop top/bottom
                    new_height = int(img.width / target_ratio)
                    top = (img.height - new_height) / 2
                    img = img.crop((0, top, img.width, top + new_height))

                # Finally, resize precisely to 720x1280
                resample = getattr(Image, "Resampling", Image).LANCZOS
                img = img.resize((720, 1280), resample)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(filepath, "JPEG")
                logger.info("Processed %s to 720x1280 (720p HD)", filepath.name)
        except Exception as e:
            logger.error("Failed to process image %s: %s", filepath.name, e)

    async def _generate_scenery(
        self, prompt: str, temp_dir: Path, idx: int, total_scenes: int = 5
    ) -> Path:
        """Generate high-quality scene image via Pollinations AI (720p HD)."""
        import time
        from urllib.parse import quote

        filename = temp_dir / f"scene_{idx}.jpg"
        styled_prompt = f"{prompt}, cinematic lighting, photorealistic, highly detailed, 4k"
        encoded_prompt = quote(styled_prompt)
        seed = random.randint(1000, 999999)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        print("\n[IMAGE MODEL] ----------------------------------------------------", flush=True)
        print(
            f"[IMAGE MODEL] >>> SCENE {idx+1}/{total_scenes}: Starting Visual Generation (720p HD)",
            flush=True,
        )
        print(f'[IMAGE MODEL] Prompt: "{prompt[:90]}..."', flush=True)
        print(
            "[IMAGE MODEL] Calling Primary Model: Pollinations FLUX (https://image.pollinations.ai/prompt/... | model=flux)",
            flush=True,
        )

        # 1. Primary: Cloudflare Workers AI FLUX (if credentials configured)
        if settings.cloudflare_account_id and settings.cloudflare_ai_token:
            try:
                from src.services.cloudflare_image_service import CloudflareImageService

                t_cf = time.time()
                print(
                    "[IMAGE MODEL] Calling Primary Model: Cloudflare Workers AI (@cf/black-forest-labs/flux-1-schnell)...",
                    flush=True,
                )
                async with CloudflareImageService() as cf:
                    cf_bytes = await cf.generate_from_text(styled_prompt, steps=4)
                    if cf_bytes and len(cf_bytes) > 2000:
                        filename.write_bytes(cf_bytes)
                        self._crop_and_resize_to_720_1280(filename)
                        dur = round(time.time() - t_cf, 2)
                        print(
                            f"[IMAGE MODEL] [SUCCESS] Scene {idx+1}/{total_scenes} rendered via Cloudflare Flux in {dur}s ({len(cf_bytes):,} bytes)",
                            flush=True,
                        )
                        print(
                            "[IMAGE MODEL] ----------------------------------------------------\n",
                            flush=True,
                        )
                        return filename
            except Exception as cf_err:
                print(
                    f"[IMAGE MODEL] [WARNING] Cloudflare Workers AI Flux error: {cf_err}. Trying Pollinations fallback...",
                    flush=True,
                )

        # 2. Secondary: Pollinations FLUX
        t_start = time.time()
        flux_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=720&height=1280&model=flux&nologo=true&seed={seed}"
        print("[IMAGE MODEL] Calling Model: Pollinations FLUX (model=flux)...", flush=True)
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(flux_url, headers=headers, timeout=25.0)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    filename.write_bytes(resp.content)
                    self._crop_and_resize_to_720_1280(filename)
                    dur = round(time.time() - t_start, 2)
                    print(
                        f"[IMAGE MODEL] [SUCCESS] Scene {idx+1}/{total_scenes} rendered via Pollinations FLUX in {dur}s ({len(resp.content):,} bytes)",
                        flush=True,
                    )
                    print(
                        "[IMAGE MODEL] ----------------------------------------------------\n",
                        flush=True,
                    )
                    return filename
                else:
                    print(
                        f"[IMAGE MODEL] [WARNING] Pollinations FLUX returned HTTP status {resp.status_code}. Trying turbo fallback...",
                        flush=True,
                    )
        except Exception as flux_err:
            print(
                f"[IMAGE MODEL] [WARNING] Pollinations FLUX request error: {flux_err}. Trying turbo fallback...",
                flush=True,
            )

        # 3. Tertiary: Pollinations Turbo
        t_turbo = time.time()
        turbo_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=720&height=1280&model=turbo&nologo=true&seed={seed}"
        print("[IMAGE MODEL] Calling Fallback Model: Pollinations Turbo (model=turbo)", flush=True)
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(turbo_url, headers=headers, timeout=15.0)
                if resp.status_code == 200 and len(resp.content) > 500:
                    filename.write_bytes(resp.content)
                    self._crop_and_resize_to_720_1280(filename)
                    dur = round(time.time() - t_turbo, 2)
                    print(
                        f"[IMAGE MODEL] [SUCCESS] Scene {idx+1}/{total_scenes} rendered via Pollinations Turbo in {dur}s ({len(resp.content):,} bytes)",
                        flush=True,
                    )
                    print(
                        "[IMAGE MODEL] ----------------------------------------------------\n",
                        flush=True,
                    )
                    return filename
        except Exception as e:
            print(f"[IMAGE MODEL] [WARNING] Pollinations Turbo timed out / error ({e})", flush=True)

        # 4. Continuity Fallback: If a previous scene exists, reuse it to maintain visual immersion
        prev_scene = temp_dir / f"scene_{idx-1}.jpg"
        if idx > 0 and prev_scene.exists():
            import shutil as _shutil

            _shutil.copy2(prev_scene, filename)
            print(
                f"[IMAGE MODEL] [FALLBACK] Reusing previous scene visual for Scene {idx+1}/{total_scenes}",
                flush=True,
            )
            print("[IMAGE MODEL] ----------------------------------------------------\n", flush=True)
            return filename

        # 5. High-Resolution Modern Cinematic Gradient (Emergency Fallback)
        print(
            f"[IMAGE MODEL] [FALLBACK] Applying high-res cinematic backdrop for Scene {idx+1}/{total_scenes}",
            flush=True,
        )
        print("[IMAGE MODEL] ----------------------------------------------------\n", flush=True)
        try:
            fallback_img = Image.new("RGB", (720, 1280), color=(18, 30, 49))
            draw = ImageDraw.Draw(fallback_img)
            for y in range(1280):
                r = int(14 + (y / 1280.0) * 15)
                g = int(24 + (y / 1280.0) * 20)
                b = int(42 + (y / 1280.0) * 35)
                draw.line([(0, y), (720, y)], fill=(r, g, b))
            fallback_img.save(filename, "JPEG")
            return filename
        except Exception as fb_err:
            raise VideoGenerationError(f"Failed to generate frame {idx}: {fb_err}") from fb_err

    def _align_words_with_text(self, stream_words: list[dict], original_text: str) -> list[dict]:
        """Align stream WordBoundary tokens with the original punctuated text."""
        raw_tokens = original_text.strip().split()
        aligned = []
        token_idx = 0
        total_tokens = len(raw_tokens)

        for sw in stream_words:
            w_clean = re.sub(r"[^\w]", "", sw.get("text", "")).lower()
            start = sw.get("offset", 0) / 10_000_000.0
            dur = sw.get("duration", 0) / 10_000_000.0
            end = start + dur

            display_word = sw.get("text", "")
            for j in range(token_idx, min(token_idx + 4, total_tokens)):
                t_clean = re.sub(r"[^\w]", "", raw_tokens[j]).lower()
                if t_clean == w_clean:
                    display_word = raw_tokens[j]
                    token_idx = j + 1
                    break

            aligned.append({"word": display_word, "start": start, "end": end, "duration": dur})
        return aligned

    def _chunk_words_for_subtitles(
        self, words: list[dict], max_words: int = 5, max_chars_per_line: int = 24
    ) -> list[dict]:
        """
        Groups words into short, natural caption chunks:
        - Target 4 to 6 words per chunk (maximum 1 to 2 lines)
        - Breaks on terminal punctuation (. ! ?) and prominent speech pauses (>= 0.3s)
        - Subdivides long phrases into balanced parts to prevent awkward 1-word orphan lines
        - Enforces strict non-overlapping audio timestamps so captions vanish during pauses
        - Ensures maximum 2 lines on screen at any single moment
        """
        if not words:
            return []

        # 1. Segment words by terminal punctuation or audio pauses
        sentences = []
        curr_sent = []

        for i, w in enumerate(words):
            curr_sent.append(w)
            word_text = w["word"].strip()
            is_terminal = bool(re.search(r"[.!?]$", word_text))

            has_pause = False
            if i < len(words) - 1:
                gap = words[i + 1]["start"] - w["end"]
                if gap >= 0.30:
                    has_pause = True

            if is_terminal or has_pause:
                sentences.append(curr_sent)
                curr_sent = []

        if curr_sent:
            sentences.append(curr_sent)

        # 2. Divide into short, balanced chunks of maximum 4 to 6 words
        chunks = []
        for sent in sentences:
            if not sent:
                continue

            n = len(sent)
            if n <= max_words:
                chunks.append(sent)
            else:
                # Check for comma / clause pause near the middle
                comma_idx = -1
                for idx, w in enumerate(sent[:-1]):
                    if re.search(r"[,;:]$", w["word"].strip()) and 2 <= idx <= n - 3:
                        comma_idx = idx
                        break

                if comma_idx != -1:
                    part1 = sent[: comma_idx + 1]
                    part2 = sent[comma_idx + 1 :]
                    for sub in [part1, part2]:
                        if len(sub) <= max_words:
                            chunks.append(sub)
                        else:
                            num_parts = (len(sub) + max_words - 1) // max_words
                            k, m = divmod(len(sub), num_parts)
                            sub_chunks = [
                                sub[j * k + min(j, m) : (j + 1) * k + min(j + 1, m)]
                                for j in range(num_parts)
                            ]
                            chunks.extend(sub_chunks)
                else:
                    num_parts = (n + max_words - 1) // max_words
                    k, m = divmod(n, num_parts)
                    sub_chunks = [
                        sent[j * k + min(j, m) : (j + 1) * k + min(j + 1, m)]
                        for j in range(num_parts)
                    ]
                    chunks.extend(sub_chunks)

        # 3. Format chunks into 1 or 2 lines
        result = []
        for c_words in chunks:
            if not c_words:
                continue
            start_t = round(c_words[0]["start"], 3)
            end_t = round(c_words[-1]["end"], 3)

            raw_words = [w["word"].strip() for w in c_words]

            # Max 2 lines: format line 1 and line 2 cleanly
            total_chars = sum(len(w) for w in raw_words) + len(raw_words) - 1
            if len(raw_words) <= 3 or total_chars <= max_chars_per_line:
                display_text = " ".join(raw_words)
            else:
                mid = (len(raw_words) + 1) // 2
                line1 = " ".join(raw_words[:mid])
                line2 = " ".join(raw_words[mid:])
                display_text = f"{line1}\n{line2}"

            result.append(
                {"start": start_t, "end": end_t, "text": display_text, "words_count": len(c_words)}
            )

        # 4. Strict non-overlapping enforcement and minimum display duration
        for i in range(len(result) - 1):
            if result[i]["end"] > result[i + 1]["start"]:
                result[i]["end"] = result[i + 1]["start"]
            if result[i]["end"] - result[i]["start"] < 0.25:
                result[i]["end"] = result[i]["start"] + 0.25

        return result

    def _chunk_from_cues_or_text(
        self, raw_cues: list[dict], full_text: str, audio_path: Path
    ) -> list[dict]:
        """Fallback chunker to prevent giant static blocks if WordBoundary stream is unavailable."""
        words = full_text.split()
        if not words:
            return []
        try:
            audio_clip = AudioFileClip(str(audio_path))
            total_dur = audio_clip.duration
        except Exception:
            total_dur = max(3.0, len(words) * 0.35)

        max_words = 5
        word_chunks = [words[i : i + max_words] for i in range(0, len(words), max_words)]
        chunks = []
        total_words = len(words)
        curr_time = 0.1

        for w_list in word_chunks:
            chunk_dur = (len(w_list) / total_words) * (total_dur - 0.2)
            end_time = curr_time + chunk_dur
            if len(w_list) <= 3:
                txt = " ".join(w_list)
            else:
                mid = (len(w_list) + 1) // 2
                txt = f"{' '.join(w_list[:mid])}\n{' '.join(w_list[mid:])}"
            chunks.append(
                {
                    "start": round(curr_time, 3),
                    "end": round(end_time, 3),
                    "text": txt,
                    "words_count": len(w_list),
                }
            )
            curr_time = end_time

        return chunks

    async def _generate_audio_and_subs(self, text: str, temp_dir: Path) -> tuple[Path, list[dict]]:
        """Generate AI Voiceover and synchronized subtitle chunks using edge-tts."""
        audio_file = temp_dir / "narration.mp3"
        vtt_file = temp_dir / "narration.vtt"
        clean_text = text.replace("\n", " ").strip()

        logger.info("Generating AI Voiceover and Word Timestamps...")
        print("[VIDEO PIPELINE] Synthesizing speech & word boundaries via Edge-TTS...", flush=True)

        stream_words: list[dict] = []
        communicate = edge_tts.Communicate(
            clean_text, voice="en-US-AvaNeural", rate="+10%", boundary="WordBoundary"
        )

        try:
            with open(audio_file, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        stream_words.append(chunk)
        except Exception as tts_err:
            logger.warning("edge-tts async streaming failed (%s), falling back to CLI...", tts_err)
            command = f'edge-tts --voice "en-US-AvaNeural" --rate="+10%" --text "{clean_text}" --write-media {audio_file} --write-subtitles {vtt_file}'

            def run_edge_tts_cli():
                subprocess.run(command, shell=True, check=True, capture_output=True)

            await asyncio.to_thread(run_edge_tts_cli)

        if not audio_file.exists() or audio_file.stat().st_size == 0:
            raise VideoGenerationError("Failed to generate audio file.")

        # If word boundaries were captured, align and chunk them
        if stream_words:
            aligned = self._align_words_with_text(stream_words, clean_text)
            subtitle_chunks = self._chunk_words_for_subtitles(aligned, max_words=5)
        else:
            if vtt_file.exists():
                raw_cues = self._parse_vtt(vtt_file)
                subtitle_chunks = self._chunk_from_cues_or_text(raw_cues, clean_text, audio_file)
            else:
                subtitle_chunks = self._chunk_from_cues_or_text([], clean_text, audio_file)

        # Write VTT file for reference/debugging
        try:
            vtt_lines = ["WEBVTT\n\n"]
            for idx, ch in enumerate(subtitle_chunks, 1):
                s_ms = f"{int(ch['start']//3600):02d}:{int((ch['start']%3600)//60):02d}:{int(ch['start']%60):02d}.{int((ch['start']%1)*1000):03d}"
                e_ms = f"{int(ch['end']//3600):02d}:{int((ch['end']%3600)//60):02d}:{int(ch['end']%60):02d}.{int((ch['end']%1)*1000):03d}"
                vtt_lines.append(f"{idx}\n{s_ms} --> {e_ms}\n{ch['text']}\n\n")
            vtt_file.write_text("".join(vtt_lines), encoding="utf-8")
        except Exception:
            pass

        print(
            f"[VIDEO PIPELINE] Subtitles ready: {len(subtitle_chunks)} dynamic synced chunks.",
            flush=True,
        )
        return audio_file, subtitle_chunks

    def _parse_vtt(self, vtt_file: Path) -> list[dict]:
        """Parse VTT timestamps (retained for backward compatibility)."""
        clips_data = []
        content = vtt_file.read_text(encoding="utf-8")

        pattern = re.compile(
            r"(\d{2}:\d{2}:\d{2}[.,]\d{3}) --> (\d{2}:\d{2}:\d{2}[.,]\d{3})\r?\n(.*?)(?=\r?\n\r?\n|\Z)",
            re.DOTALL,
        )
        matches = pattern.findall(content)

        def time_to_sec(t_str: str) -> float:
            h, m, s_ms = t_str.split(":")
            s_ms = s_ms.replace(",", ".")
            s, ms = s_ms.split(".")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

        for match in matches:
            start_time = time_to_sec(match[0])
            end_time = time_to_sec(match[1])
            text = match[2].strip()
            if text:
                clips_data.append({"start": start_time, "end": end_time, "text": text})
        return clips_data

    def _apply_random_motion(self, clip: ImageClip, duration: float):
        """Ultra-fast 720p positioning with cinematic crossfade transitions."""
        return clip.set_position(("center", "center"))

    def _create_text_clip_pil(self, text: str, max_width: int = 620) -> ImageClip:
        """
        Creates a high-contrast, centered caption image with a sleek semi-transparent pill badge:
        - Bold modern typography
        - Centered text alignment
        - Max 2 lines
        - White text with dark outline stroke
        - Subtle translucent rounded background badge preserving background video visibility
        """
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "arialbd.ttf",
            "arial.ttf",
            "DejaVuSans-Bold.ttf",
        ]
        font = None
        for f in font_candidates:
            if os.path.exists(f):
                try:
                    font = ImageFont.truetype(f, 36)
                    break
                except Exception:
                    continue
        if not font:
            for font_name in ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arial.ttf"]:
                try:
                    font = ImageFont.truetype(font_name, 36)
                    break
                except Exception:
                    continue
        if not font:
            try:
                font = ImageFont.load_default(size=36)
            except Exception:
                font = ImageFont.load_default()

        temp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(temp_img)

        # Ensure max 2 lines
        raw_lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(raw_lines) > 2:
            raw_lines = [raw_lines[0], " ".join(raw_lines[1:])]
        wrapped_text = "\n".join(raw_lines)

        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center", spacing=8)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        pad_x = 28
        pad_y = 16
        box_w = int(text_w + pad_x * 2)
        box_h = int(text_h + pad_y * 2)

        img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Translucent rounded pill badge: dark charcoal with ~75% opacity, subtle border
        draw.rounded_rectangle(
            [(0, 0), (box_w - 1, box_h - 1)],
            radius=18,
            fill=(15, 20, 28, 190),
            outline=(255, 255, 255, 50),
            width=1,
        )

        # Center text inside the box
        draw_x = box_w // 2
        draw_y = pad_y - bbox[1]

        # Draw centered text with subtle stroke
        draw.multiline_text(
            (draw_x, draw_y),
            wrapped_text,
            font=font,
            fill=(255, 255, 255, 255),
            align="center",
            anchor="ma",
            spacing=8,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 240),
        )

        return ImageClip(np.array(img))

    def _build_and_render(
        self,
        subtitle_data: list[dict],
        scene_img_paths: list[Path],
        audio_path: Path,
        bgm_path: Path | None,
        output_file: Path,
    ):
        """Construct the MoviePy video and render it. Runs synchronously in a thread."""
        logger.info("Assembling Video Clips...")
        audio_clip = AudioFileClip(str(audio_path))

        if bgm_path and bgm_path.exists():
            try:
                import moviepy.audio.fx.all as afx

                raw_bgm = AudioFileClip(str(bgm_path))
                bgm_clip = raw_bgm.fx(afx.volumex, 0.1).set_duration(audio_clip.duration)
                final_audio = CompositeAudioClip([bgm_clip, audio_clip])
            except Exception as bgm_err:
                logger.warning("Could not mix BGM clip (%s), using narration audio only.", bgm_err)
                final_audio = audio_clip
        else:
            final_audio = audio_clip

        # Sequence ALL generated scene images into the video timeline
        scene_clips = []
        num_scenes = len(scene_img_paths)
        total_duration = audio_clip.duration
        # Strict duration cap: Reel / commercial video must never exceed 24.0 seconds
        if total_duration > 24.0:
            print(
                f"[VIDEO PIPELINE] Capping duration to 24.0s (was {round(total_duration, 1)}s)",
                flush=True,
            )
            total_duration = 24.0
            final_audio = final_audio.subclip(0, 24.0)

        scene_duration = total_duration / max(num_scenes, 1)

        print(
            f"[VIDEO PIPELINE] Assembling {num_scenes} distinct scenes across {round(total_duration, 1)}s video timeline...",
            flush=True,
        )

        for idx, img_path in enumerate(scene_img_paths):
            start_t = idx * scene_duration
            # Ensure the last clip covers through to the end of the audio
            clip_dur = (
                (total_duration - start_t) if idx == num_scenes - 1 else (scene_duration + 0.4)
            )

            clip = ImageClip(str(img_path)).set_duration(clip_dur)
            clip = self._apply_random_motion(clip, clip_dur)
            clip = clip.set_start(start_t)
            if idx > 0:
                clip = fadein(clip, 0.4)
            scene_clips.append(clip)

        # Build subtitle text overlay layers timed to speech
        text_layers = []
        target_y = 1000  # Positioned in the lower third (approx 78% down 720x1280 canvas), below focal action
        for data in subtitle_data:
            if data["start"] >= total_duration:
                continue
            chunk_end = min(data["end"], total_duration)
            dur = max(0.1, chunk_end - data["start"])
            if dur <= 0:
                continue

            txt_clip = self._create_text_clip_pil(data["text"])
            txt_clip = (
                txt_clip.set_position(("center", target_y))
                .set_start(data["start"])
                .set_duration(dur)
            )
            text_layers.append(txt_clip)

        if not scene_clips:
            raise VideoGenerationError("No valid scenes generated.")

        video_layers = scene_clips + text_layers
        final_video = CompositeVideoClip(video_layers, size=(720, 1280))
        final_video = final_video.set_audio(final_audio)

        threads_count = min(8, max(2, os.cpu_count() or 4))
        print(
            f"[VIDEO PIPELINE] Step 4: Compositing 720p HD MP4 (720x1280) via MoviePy & FFmpeg ({threads_count} threads)...",
            flush=True,
        )
        final_video.write_videofile(
            str(output_file),
            fps=24,
            threads=threads_count,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            remove_temp=False,
            ffmpeg_params=["-pix_fmt", "yuv420p"],
            logger=None,
        )

    async def generate_campaign_video(self, campaign_id: str, scenes: list[VideoScene]) -> str:
        """
        Main entry point.
        1. Rate limiting via semaphore.
        2. Temp directory isolation.
        3. Try/finally cleanup.
        4. Upload to Supabase.
        """
        if not scenes:
            raise ValueError("No scenes provided for video generation.")

        # Ensure narration sentences are cleanly punctuated so edge-tts pauses naturally
        formatted_narrations = []
        for s in scenes:
            narr = s.narration.strip()
            if narr and not narr.endswith((".", "!", "?")):
                narr += "."
            formatted_narrations.append(narr)
        full_script = " ".join(formatted_narrations)

        logger.info("Waiting for video render semaphore...")
        async with _render_semaphore:
            print(f"[VIDEO PIPELINE] Acquired render lock for campaign: {campaign_id}", flush=True)
            temp_dir = tempfile.mkdtemp(prefix=f"video_{campaign_id}_")
            temp_path = Path(temp_dir)

            try:
                # 1. Parallelize Audio and BGM (which don't hit rate limits)
                print(
                    "[VIDEO PIPELINE] Step 2: Synthesizing neural voiceover via Edge-TTS...",
                    flush=True,
                )
                audio_task = self._generate_audio_and_subs(full_script, temp_path)
                bgm_task = self._download_bgm(temp_path)

                audio_res, bgm_res = await asyncio.gather(audio_task, bgm_task)

                audio_path, subtitle_data = audio_res
                bgm_path = bgm_res
                print("[VIDEO PIPELINE] Voiceover & Subtitles ready.", flush=True)

                # 2. Sequential Image Generation via Pollinations AI
                print(
                    f"[VIDEO PIPELINE] Step 3: Generating visuals for {len(scenes)} scenes via Pollinations AI...",
                    flush=True,
                )
                scene_paths = []
                for idx, scene in enumerate(scenes):
                    p = await self._generate_scenery(
                        scene.image_prompt, temp_path, idx, len(scenes)
                    )
                    if p:
                        scene_paths.append(p)
                    await asyncio.sleep(0.5)  # brief pause between scenes

                if not scene_paths:
                    raise VideoGenerationError("Failed to generate any scene images.")

                # 4. Render Video (with Timeout)
                output_file = temp_path / f"campaign_{campaign_id}.mp4"
                print(
                    "[VIDEO PIPELINE] Step 4: Compositing 1080p MP4 via MoviePy & FFmpeg...",
                    flush=True,
                )
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(
                            self._build_and_render,
                            subtitle_data,
                            scene_paths,
                            audio_path,
                            bgm_path,
                            output_file,
                        ),
                        timeout=settings.video_render_timeout_seconds,
                    )
                except TimeoutError:
                    raise VideoGenerationError("Video rendering timed out.") from None

                # 5. Upload to Supabase (with unique path and upsert=true)
                logger.info("Uploading video to Supabase...")
                import time as _time
                timestamp = int(_time.time())
                storage_name = f"{campaign_id}/campaign_{campaign_id}_{timestamp}.mp4"

                try:
                    with open(output_file, "rb") as f:
                        self.supabase.storage.from_(self.bucket).upload(
                            storage_name,
                            f,
                            file_options={"content-type": "video/mp4", "upsert": "true"},
                        )
                    public_url = str(
                        self.supabase.storage.from_(self.bucket).get_public_url(storage_name)
                    )
                    logger.info("Video successfully uploaded to Supabase: %s", public_url)
                    return public_url
                except Exception as upload_err:
                    logger.error("Supabase upload failed: %s", upload_err, exc_info=True)
                    # If Supabase upload fails, check if local static serving is possible
                    static_dir = Path(__file__).parent.parent.parent / "static" / "videos"
                    static_dir.mkdir(parents=True, exist_ok=True)
                    local_filename = f"campaign_{campaign_id}_{timestamp}.mp4"
                    local_path = static_dir / local_filename
                    import shutil as _shutil

                    _shutil.copy2(output_file, local_path)

                    render_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
                    if not render_url and "onrender.com" in os.environ.get("BASE_URL", ""):
                        render_url = os.environ["BASE_URL"].rstrip("/")
                    if not render_url:
                        # Fallback to known Render URL for this project
                        render_url = "https://ai-powered-marketting-agent.onrender.com"

                    local_url = f"{render_url}/static/videos/{local_filename}"
                    logger.info("Video saved locally as fallback: %s", local_url)
                    return local_url

            finally:
                # Cleanup Temp Directory
                import shutil

                shutil.rmtree(temp_path, ignore_errors=True)
                logger.info("Cleaned up temp directory %s", temp_path)
