#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
么ＴＩＧＥＲ_ＳＨＡWツ - Video Downloader
Ultra-Fast Multi-Platform Video Downloader
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import re

try:
    import yt_dlp
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp", "-q"])
    import yt_dlp

try:
    from rich.console import Console
    from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, TextColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich import box
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, TextColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich import box

console = Console()

BANNER = """
[bold yellow]
  ╔══════════════════════════════════════════════════════╗
  ║   么 ＴＩＧＥＲ＿ＳＨＡＷツ  VIDEO  DOWNLOADER   ║
  ║        ⚡ Ultra Fast • Multi-Platform • HD ⚡       ║
  ╚══════════════════════════════════════════════════════╝
[/bold yellow]
"""

SUPPORTED_SITES = [
    "YouTube", "TikTok", "Instagram", "Twitter/X", "Facebook",
    "Vimeo", "Twitch", "Reddit", "Dailymotion", "SoundCloud",
    "و 1000+ موقع آخر"
]


class TigerShawDownloader:
    def __init__(self):
        self.download_dir = Path.home() / "Downloads" / "TIGER_SHAW"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.download_dir / "history.json"
        self.history = self._load_history()
        self.max_concurrent = 5  # أقصى تحميل متزامن

    def _load_history(self):
        if self.history_file.exists():
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_history(self, entry):
        self.history.append(entry)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def show_banner(self):
        console.print(BANNER)

    def get_video_info(self, url):
        """جلب معلومات الفيديو قبل التحميل"""
        ydl_opts = {"quiet": True, "no_warnings": True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            console.print(f"[red]❌ خطأ في جلب المعلومات: {e}[/red]")
            return None

    def show_formats(self, url):
        """عرض جميع الجودات المتاحة"""
        info = self.get_video_info(url)
        if not info:
            return None

        console.print(f"\n[bold cyan]📹 العنوان:[/bold cyan] {info.get('title', 'غير معروف')}")
        console.print(f"[bold cyan]⏱️  المدة:[/bold cyan] {info.get('duration_string', 'غير معروف')}")
        console.print(f"[bold cyan]👤 القناة:[/bold cyan] {info.get('uploader', 'غير معروف')}\n")

        table = Table(title="🎬 الجودات المتاحة", box=box.ROUNDED, style="bold")
        table.add_column("رقم", style="yellow", justify="center")
        table.add_column("الجودة", style="green")
        table.add_column("الامتداد", style="cyan")
        table.add_column("الحجم التقريبي", style="magenta")
        table.add_column("نوع", style="white")

        formats = info.get("formats", [])
        video_formats = []

        # فرز وتصفية الفيديوهات
        for f in formats:
            if f.get("vcodec") != "none" and f.get("height"):
                size = f.get("filesize") or f.get("filesize_approx") or 0
                size_str = f"{size / 1024 / 1024:.1f} MB" if size else "غير معروف"
                video_formats.append({
                    "format_id": f["format_id"],
                    "height": f.get("height", 0),
                    "ext": f.get("ext", ""),
                    "size": size_str,
                    "fps": f.get("fps", ""),
                })

        # ترتيب من الأعلى جودة
        video_formats.sort(key=lambda x: x["height"], reverse=True)
        # إزالة المكررات
        seen = set()
        unique_formats = []
        for f in video_formats:
            key = (f["height"], f["ext"])
            if key not in seen:
                seen.add(key)
                unique_formats.append(f)

        for i, f in enumerate(unique_formats[:15], 1):
            quality_icon = "🔥" if f["height"] >= 1080 else "⭐" if f["height"] >= 720 else "📺"
            table.add_row(
                str(i),
                f"{quality_icon} {f['height']}p",
                f["ext"],
                f["size"],
                "فيديو+صوت"
            )

        # خيارات صوت فقط
        for f in formats:
            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                size = f.get("filesize") or 0
                size_str = f"{size / 1024 / 1024:.1f} MB" if size else "غير معروف"
                unique_formats.append({
                    "format_id": f["format_id"],
                    "height": 0,
                    "ext": f.get("ext", "mp3"),
                    "size": size_str,
                    "fps": ""
                })
                table.add_row(
                    str(len(unique_formats)),
                    "🎵 صوت فقط",
                    f.get("ext", "mp3"),
                    size_str,
                    "صوت"
                )
                break

        console.print(table)
        return unique_formats

    def download_video(self, url, quality="best", output_name=None, progress_callback=None):
        """تحميل فيديو واحد"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_template = str(self.download_dir / f"%(title)s_{timestamp}.%(ext)s")

        # إعدادات الجودة
        if quality == "best":
            format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        elif quality == "1080p":
            format_spec = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]"
        elif quality == "720p":
            format_spec = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]"
        elif quality == "480p":
            format_spec = "bestvideo[height<=480]+bestaudio/best[height<=480]"
        elif quality == "audio":
            format_spec = "bestaudio/best"
        else:
            format_spec = quality

        ydl_opts = {
            "format": format_spec,
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "concurrent_fragment_downloads": 16,  # ⚡ أقصى سرعة
            "http_chunk_size": 10485760,           # 10MB chunks
            "retries": 10,
            "fragment_retries": 10,
            "postprocessors": [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }] if quality != "audio" else [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        }

        downloaded_file = [None]
        start_time = time.time()

        def progress_hook(d):
            if d["status"] == "finished":
                downloaded_file[0] = d.get("filename")

        ydl_opts["progress_hooks"] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "فيديو")

            elapsed = time.time() - start_time
            entry = {
                "title": title,
                "url": url,
                "quality": quality,
                "date": datetime.now().isoformat(),
                "duration": elapsed,
                "status": "success"
            }
            self._save_history(entry)
            return True, title, elapsed

        except Exception as e:
            return False, str(e), 0

    def batch_download(self, urls, quality="best"):
        """تحميل متعدد متزامن - أقصى تحميل"""
        console.print(f"\n[bold yellow]⚡ تحميل {len(urls)} فيديو بالتوازي (أقصى {self.max_concurrent} في آن واحد)[/bold yellow]\n")

        results = {"success": 0, "failed": 0, "files": []}
        lock = threading.Lock()

        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=30),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            main_task = progress.add_task(
                f"[yellow]么TIGER_SHAWツ - تحميل جماعي",
                total=len(urls)
            )

            def download_one(url_item):
                idx, url = url_item
                success, title, elapsed = self.download_video(url, quality)
                with lock:
                    if success:
                        results["success"] += 1
                        results["files"].append(title)
                        console.print(f"  [green]✅ [{idx}] {title[:50]}...[/green]")
                    else:
                        results["failed"] += 1
                        console.print(f"  [red]❌ [{idx}] فشل: {title[:50]}[/red]")
                    progress.advance(main_task)

            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                futures = [executor.submit(download_one, (i+1, url)) for i, url in enumerate(urls)]
                for future in as_completed(futures):
                    future.result()

        return results

    def show_history(self):
        """عرض سجل التحميلات"""
        if not self.history:
            console.print("[yellow]📭 لا يوجد سجل تحميلات بعد[/yellow]")
            return

        table = Table(title="📋 سجل التحميلات", box=box.ROUNDED)
        table.add_column("العنوان", style="cyan", max_width=40)
        table.add_column("الجودة", style="green")
        table.add_column("التاريخ", style="yellow")
        table.add_column("الحالة", style="white")

        for entry in reversed(self.history[-20:]):
            status = "[green]✅ نجح[/green]" if entry["status"] == "success" else "[red]❌ فشل[/red]"
            date = entry["date"][:16].replace("T", " ")
            table.add_row(entry["title"][:40], entry["quality"], date, status)

        console.print(table)

    def interactive_menu(self):
        """القائمة التفاعلية الرئيسية"""
        self.show_banner()

        # عرض المواقع المدعومة
        sites_text = " • ".join(SUPPORTED_SITES)
        console.print(Panel(f"[dim]{sites_text}[/dim]", title="[bold green]🌍 المواقع المدعومة[/bold green]"))

        console.print(f"\n[bold cyan]📁 مجلد التحميل:[/bold cyan] {self.download_dir}\n")

        while True:
            console.print("\n[bold yellow]═══ القائمة الرئيسية ═══[/bold yellow]")
            console.print("[1] ⬇️  تحميل فيديو واحد")
            console.print("[2] 📋 تحميل متعدد (روابط)")
            console.print("[3] 🎵 تحميل صوت فقط (MP3)")
            console.print("[4] 📜 سجل التحميلات")
            console.print("[5] ⚙️  إعدادات")
            console.print("[0] 🚪 خروج")

            choice = console.input("\n[bold]اختر: [/bold]").strip()

            if choice == "1":
                self._menu_single_download()
            elif choice == "2":
                self._menu_batch_download()
            elif choice == "3":
                self._menu_audio_download()
            elif choice == "4":
                self.show_history()
            elif choice == "5":
                self._menu_settings()
            elif choice == "0":
                console.print("\n[bold yellow]么 شكراً لاستخدام TIGER_SHAWツ ⚡[/bold yellow]\n")
                break
            else:
                console.print("[red]اختيار غير صحيح[/red]")

    def _menu_single_download(self):
        url = console.input("\n[bold cyan]🔗 أدخل الرابط: [/bold cyan]").strip()
        if not url:
            return

        console.print("\n[dim]جاري جلب معلومات الفيديو...[/dim]")
        formats = self.show_formats(url)
        if not formats:
            return

        console.print("\n[bold]اختر الجودة:[/bold]")
        console.print("[1] 🔥 أعلى جودة (best)")
        console.print("[2] 🎬 1080p")
        console.print("[3] 📺 720p")
        console.print("[4] 📱 480p")
        console.print("[5] 🎵 صوت فقط MP3")

        q_choice = console.input("[bold]جودة: [/bold]").strip()
        quality_map = {"1": "best", "2": "1080p", "3": "720p", "4": "480p", "5": "audio"}
        quality = quality_map.get(q_choice, "best")

        console.print(f"\n[bold yellow]⚡ جاري التحميل بجودة {quality}...[/bold yellow]")
        success, title, elapsed = self.download_video(url, quality)

        if success:
            console.print(f"\n[bold green]✅ تم التحميل بنجاح![/bold green]")
            console.print(f"[green]📁 الملف: {title}[/green]")
            console.print(f"[green]⏱️  الوقت: {elapsed:.1f} ثانية[/green]")
            console.print(f"[green]📂 المسار: {self.download_dir}[/green]")
        else:
            console.print(f"\n[red]❌ فشل التحميل: {title}[/red]")

    def _menu_batch_download(self):
        console.print("\n[bold cyan]📋 أدخل الروابط (رابط في كل سطر، اكتب 'done' للانتهاء):[/bold cyan]")
        urls = []
        while True:
            url = console.input(f"  [{len(urls)+1}] ").strip()
            if url.lower() == "done" or url == "":
                break
            if url.startswith("http"):
                urls.append(url)

        if not urls:
            console.print("[yellow]لم تدخل أي روابط[/yellow]")
            return

        console.print("\n[bold]الجودة للجميع:[/bold]")
        console.print("[1] 🔥 أعلى جودة  [2] 1080p  [3] 720p  [4] 480p")
        q_choice = console.input("[bold]جودة: [/bold]").strip()
        quality_map = {"1": "best", "2": "1080p", "3": "720p", "4": "480p"}
        quality = quality_map.get(q_choice, "best")

        results = self.batch_download(urls, quality)

        console.print(f"\n[bold green]✅ نجح: {results['success']}[/bold green] | [bold red]❌ فشل: {results['failed']}[/bold red]")
        console.print(f"[cyan]📂 المجلد: {self.download_dir}[/cyan]")

    def _menu_audio_download(self):
        url = console.input("\n[bold cyan]🔗 رابط الفيديو لاستخراج الصوت: [/bold cyan]").strip()
        if not url:
            return

        console.print("\n[bold yellow]🎵 جاري استخراج الصوت بجودة 320kbps...[/bold yellow]")
        success, title, elapsed = self.download_video(url, "audio")

        if success:
            console.print(f"\n[bold green]✅ تم استخراج الصوت بنجاح![/bold green]")
            console.print(f"[green]🎵 {title}[/green]")
        else:
            console.print(f"\n[red]❌ فشل: {title}[/red]")

    def _menu_settings(self):
        console.print(f"\n[bold cyan]⚙️  الإعدادات الحالية:[/bold cyan]")
        console.print(f"  📁 مجلد التحميل: {self.download_dir}")
        console.print(f"  ⚡ أقصى تحميل متزامن: {self.max_concurrent}")
        console.print(f"  🔗 أجزاء متوازية: 16 (أقصى سرعة)")

        new_concurrent = console.input(f"\n[bold]أقصى تحميل متزامن (1-10) [{self.max_concurrent}]: [/bold]").strip()
        if new_concurrent.isdigit() and 1 <= int(new_concurrent) <= 10:
            self.max_concurrent = int(new_concurrent)
            console.print(f"[green]✅ تم التغيير إلى {self.max_concurrent}[/green]")


def main():
    downloader = TigerShawDownloader()

    # تشغيل CLI أو تفاعلي
    if len(sys.argv) > 1:
        url = sys.argv[1]
        quality = sys.argv[2] if len(sys.argv) > 2 else "best"
        downloader.show_banner()
        console.print(f"[bold yellow]⚡ تحميل: {url} [{quality}][/bold yellow]")
        success, title, elapsed = downloader.download_video(url, quality)
        if success:
            console.print(f"[green]✅ {title} - {elapsed:.1f}s[/green]")
        else:
            console.print(f"[red]❌ {title}[/red]")
    else:
        downloader.interactive_menu()


if __name__ == "__main__":
    main()
