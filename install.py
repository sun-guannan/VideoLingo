import os, sys
import platform
import subprocess
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

ascii_logo = """
__     ___     _            _     _                    
\ \   / (_) __| | ___  ___ | |   (_)_ __   __ _  ___  
 \ \ / /| |/ _` |/ _ \/ _ \| |   | | '_ \ / _` |/ _ \ 
  \ V / | | (_| |  __/ (_) | |___| | | | | (_| | (_) |
   \_/  |_|\__,_|\___|\___/|_____|_|_| |_|\__, |\___/ 
                                          |___/        
"""

def install_package(*packages):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])

def check_nvidia_gpu():
    install_package("pynvml")
    import pynvml
    from translations.translations import translate as t
    initialized = False
    try:
        pynvml.nvmlInit()
        initialized = True
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            print(t("Detected NVIDIA GPU(s)"))
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                print(f"GPU {i}: {name}")
            return True
        else:
            print(t("No NVIDIA GPU detected"))
            return False
    except pynvml.NVMLError:
        print(t("No NVIDIA GPU detected or NVIDIA drivers not properly installed"))
        return False
    finally:
        if initialized:
            pynvml.nvmlShutdown()

def check_ffmpeg():
    from rich.console import Console
    from rich.panel import Panel
    from translations.translations import translate as t
    console = Console()

    try:
        # Check if ffmpeg is installed
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        console.print(Panel(t("✅ FFmpeg is already installed"), style="green"))
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        system = platform.system()
        install_cmd = ""
        
        if system == "Windows":
            install_cmd = "choco install ffmpeg"
            extra_note = t("Install Chocolatey first (https://chocolatey.org/)")
        elif system == "Darwin":
            install_cmd = "brew install ffmpeg"
            extra_note = t("Install Homebrew first (https://brew.sh/)")
        elif system == "Linux":
            install_cmd = "sudo apt install ffmpeg  # Ubuntu/Debian\nsudo yum install ffmpeg  # CentOS/RHEL"
            extra_note = t("Use your distribution's package manager")
        
        console.print(Panel.fit(
            t("❌ FFmpeg not found\n\n") +
            f"{t('🛠️ Install using:')}\n[bold cyan]{install_cmd}[/bold cyan]\n\n" +
            f"{t('💡 Note:')}\n{extra_note}\n\n" +
            f"{t('🔄 After installing FFmpeg, please run this installer again:')}\n[bold cyan]python install.py[/bold cyan]",
            style="red"
        ))
        raise SystemExit(t("FFmpeg is required. Please install it and run the installer again."))

def main():
    install_package("requests", "rich", "ruamel.yaml", "InquirerPy")
    from rich.console import Console
    from rich.panel import Panel
    from rich.box import DOUBLE
    from InquirerPy import inquirer
    from translations.translations import translate as t
    from translations.translations import DISPLAY_LANGUAGES
    from core.utils.config_utils import load_key, update_key
    from core.utils.decorator import except_handler

    console = Console()
    
    width = max(len(line) for line in ascii_logo.splitlines()) + 4
    welcome_panel = Panel(
        ascii_logo,
        width=width,
        box=DOUBLE,
        title="[bold green]🌏[/bold green]",
        border_style="bright_blue"
    )
    console.print(welcome_panel)
    # Language selection
    current_language = load_key("display_language")
    # Find the display name for current language code
    current_display = next((k for k, v in DISPLAY_LANGUAGES.items() if v == current_language), "🇬🇧 English")
    selected_language = DISPLAY_LANGUAGES[inquirer.select(
        message="Select language / 选择语言 / 選擇語言 / 言語を選択 / Seleccionar idioma / Sélectionner la langue / Выберите язык:",
        choices=list(DISPLAY_LANGUAGES.keys()),
        default=current_display
    ).execute()]
    update_key("display_language", selected_language)

    console.print(Panel.fit(t("🚀 Starting Installation"), style="bold magenta"))

    # Configure mirrors
    # add a check to ask user if they want to configure mirrors
    if inquirer.confirm(
        message=t("Do you need to auto-configure PyPI mirrors? (Recommended if you have difficulty accessing pypi.org)"),
        default=True
    ).execute():
        from core.utils.pypi_autochoose import main as choose_mirror
        choose_mirror()

    # Detect system and GPU
    has_gpu = platform.system() != 'Darwin' and check_nvidia_gpu()
    if has_gpu:
        console.print(Panel(t("🎮 NVIDIA GPU detected, installing CUDA version of PyTorch..."), style="cyan"))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch==2.0.0", "torchaudio==2.0.0", "--index-url", "https://download.pytorch.org/whl/cu118"])
    else:
        system_name = "🍎 MacOS" if platform.system() == 'Darwin' else "💻 No NVIDIA GPU"
        console.print(Panel(t(f"{system_name} detected, installing CPU version of PyTorch... Note: it might be slow during whisperX transcription."), style="cyan"))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch==2.1.2", "torchaudio==2.1.2"])

    @except_handler("Failed to install project")
    def install_requirements():
        console.print(Panel(t("Installing project in editable mode using `pip install -e .`"), style="cyan"))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."], env={**os.environ, "PIP_NO_CACHE_DIR": "0", "PYTHONIOENCODING": "utf-8"})

    @except_handler("Failed to install Noto fonts")
    def install_noto_font():
        # Detect Linux distribution type
        if os.path.exists('/etc/debian_version'):
            # Debian/Ubuntu systems
            cmd = ['sudo', 'apt-get', 'install', '-y', 'fonts-noto']
            pkg_manager = "apt-get"
        elif os.path.exists('/etc/redhat-release'):
            # RHEL/CentOS/Fedora systems
            cmd = ['sudo', 'yum', 'install', '-y', 'google-noto*']
            pkg_manager = "yum"
        else:
            console.print("Warning: Unrecognized Linux distribution, please install Noto fonts manually", style="yellow")
            return

        subprocess.run(cmd, check=True)
        console.print(f"✅ Successfully installed Noto fonts using {pkg_manager}", style="green")

    if platform.system() == 'Linux':
        install_noto_font()
    
    install_requirements()
    check_ffmpeg()
    
    # 询问是否安装CapCutAPI
    @except_handler("Failed to install CapCutAPI")
    def install_capcut_api():
        # 询问是否需要安装CapCutAPI
        install_choice = inquirer.confirm(
            message=t("Do you want to install CapCutAPI? This allows exporting translated videos to CapCut/JianYing."),
            default=True
        ).execute()
        
        if install_choice:
            console.print(Panel(t("Installing CapCutAPI..."), style="cyan"))
            
            # 检查目录是否存在，如果存在则先删除
            import shutil
            if os.path.exists("core/capcut_api"):
                shutil.rmtree("core/capcut_api")
            
            # 克隆CapCutAPI仓库
            subprocess.check_call(["git", "clone", "--depth=1", "https://github.com/sun-guannan/CapCutAPI.git", "core/capcut_api"])
            
            # 安装依赖
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "core/capcut_api/requirements.txt"])
            
            # 复制配置文件
            if not os.path.exists("core/capcut_api/config.json"):
                shutil.copy("core/capcut_api/config.json.example", "core/capcut_api/config.json")
            
            # 询问使用剪映还是剪映国际版
            editor_choice = inquirer.select(
                message=t("Which editor do you use?"),
                choices=["CapCut", "JianYing (剪映中文版)"],
                default="CapCut"
            ).execute()
            
            # 根据选择修改配置文件
            with open("core/capcut_api/config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # 设置是否为国际版
            config["is_capcut_env"] = editor_choice == "CapCut (International)"
            
            # 保存修改后的配置
            with open("core/capcut_api/config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 更新VideoLingo配置
            update_key("capcut.editor", "CapCut" if editor_choice == "CapCut (International)" else "JianYing")
            
            # 记录用户是否安装CapCutAPI的标记位
            update_key("capcut.installed", install_choice)
            
            # 提示用户安装成功
            console.print(Panel(
                t("✅ CapCutAPI installed successfully!") + "\n\n" +
                t("Note: CapCutAPI will use port 9001 by default.") + "\n" +
                t("If you need to change the port, please edit core/capcut_api/config.json") + "\n" +
                t("If you need to switch between CapCut and JianYing, you can modify the 'is_capcut_env' setting in the same file."),
                style="green"
            ))
    
    # 安装CapCutAPI
    install_capcut_api()
    
    # First panel with installation complete and startup command
    panel1_text = (
        t("Installation completed") + "\n\n" +
        t("Now I will run this command to start the application:") + "\n" +
        "[bold]streamlit run st.py[/bold]\n" +
        t("Note: First startup may take up to 1 minute")
    )
    console.print(Panel(panel1_text, style="bold green"))

    # Second panel with troubleshooting tips
    panel2_text = (
        t("If the application fails to start:") + "\n" +
        "1. " + t("Check your network connection") + "\n" +
        "2. " + t("Re-run the installer: [bold]python install.py[/bold]")
    )
    console.print(Panel(panel2_text, style="yellow"))

    # start the application
    subprocess.Popen(["streamlit", "run", "st.py"])

if __name__ == "__main__":
    main()
