import os
import subprocess
import shutil
import sys

def build():
    print("🚀 Starting build process for Mirage...")

    # Ensure we are in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # 1. Check for ffmpeg binaries
    ffmpeg_path = os.path.join(project_root, "bin", "ffmpeg.exe")
    ffprobe_path = os.path.join(project_root, "bin", "ffprobe.exe")
    
    if not os.path.exists(ffmpeg_path) or not os.path.exists(ffprobe_path):
        print("❌ Error: ffmpeg.exe or ffprobe.exe not found in 'bin' folder.")
        print("Please copy them there before building.")
        return

    # 2. Prepare PyInstaller command
    icon_path = os.path.join("src", "assets", "favicon.ico")
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--windowed",
        "--onefile",
        "--add-data", f"bin{os.pathsep}bin",
        "--add-data", f"src{os.pathsep}src",
        f"--name=Mirage",
    ]
    
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
    
    cmd.append("main.py")

    print(f"📦 Running PyInstaller command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Build complete! You can find Mirage.exe in the 'dist' folder.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with error code {e.returncode}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        # Cleanup
        for folder in ["build", "dist"]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
        if os.path.exists("Mirage.spec"):
            os.remove("Mirage.spec")
        print("🧹 Cleanup complete.")
    else:
        build()
