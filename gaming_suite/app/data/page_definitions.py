"""
Central data definitions for all pages and their settings.
Each page is a dict with title, icon, color, and sections.
Each section has a title, icon, and list of settings.
Each setting has: id, title, description, effect, recommendation, risk, category, type.
"""

FPS_PAGE = {
    "id": "fps",
    "title": "FPS OPTIMIZER",
    "subtitle": "Maximize your framerate",
    "icon": "⚡",
    "accent": "#00C8FF",
    "sections": [
        {
            "title": "Game Boost",
            "icon": "🚀",
            "settings": [
                {"id": "game_mode", "title": "Windows Game Mode", "description": "Dedicates system resources to the active game process.", "effect": "Up to +15% FPS in CPU-bound games", "recommendation": "Enable for all gaming sessions", "risk": "Low", "category": "FPS"},
                {"id": "hw_accel_scheduling", "title": "Hardware Accelerated GPU Scheduling", "description": "Allows the GPU to manage its own VRAM, reducing CPU latency.", "effect": "Reduces stutters and improves frame pacing", "recommendation": "Enable on NVIDIA RTX 2000+ or AMD RX 5000+", "risk": "Low", "category": "FPS"},
                {"id": "fullscreen_opt", "title": "Fullscreen Optimizations", "description": "Disables Windows fullscreen optimizations that add overhead.", "effect": "More consistent frametimes", "recommendation": "Disable for competitive titles", "risk": "Low", "category": "FPS"},
                {"id": "disable_xbox_dvr", "title": "Disable Xbox Game Bar / DVR", "description": "Turns off background recording and overlay services.", "effect": "+5-10 FPS in some games", "recommendation": "Disable when not streaming", "risk": "Low", "category": "FPS"},
                {"id": "priority_boost", "title": "Process Priority Boost", "description": "Sets game process to High CPU priority automatically.", "effect": "More consistent CPU scheduling", "recommendation": "Enable for all games", "risk": "Medium", "category": "FPS"},
            ]
        },
        {
            "title": "GPU Optimization",
            "icon": "🎮",
            "settings": [
                {"id": "gpu_power_max", "title": "GPU Power Management: Max Performance", "description": "Forces GPU to run at full clock speeds at all times.", "effect": "Eliminates frequency throttling during gameplay", "recommendation": "Enable while gaming, disable on battery", "risk": "Low", "category": "GPU"},
                {"id": "shader_cache", "title": "Shader Pre-Compilation Cache", "description": "Pre-compiles and caches shader programs to reduce stutters.", "effect": "Eliminates shader compilation stutters", "recommendation": "Always enable", "risk": "None", "category": "GPU"},
                {"id": "nvidia_reflex", "title": "NVIDIA Reflex / AMD Anti-Lag", "description": "Reduces render queue depth to minimize input-to-display latency.", "effect": "Up to 30ms latency reduction", "recommendation": "Enable in all supported games", "risk": "None", "category": "GPU"},
                {"id": "texture_filtering", "title": "Anisotropic Filtering Override", "description": "Sets texture filtering quality via driver override.", "effect": "Better image quality at no FPS cost on modern GPUs", "recommendation": "Set to 8x-16x", "risk": "None", "category": "GPU"},
                {"id": "low_latency_mode", "title": "Ultra-Low Latency Mode", "description": "Limits pre-rendered frames to 1, reducing GPU queue depth.", "effect": "Reduces input lag by 10-20ms", "recommendation": "Enable for competitive play", "risk": "Low", "category": "GPU"},
            ]
        },
        {
            "title": "CPU Optimization",
            "icon": "🔧",
            "settings": [
                {"id": "cpu_affinity_boost", "title": "CPU Affinity Optimization", "description": "Assigns game threads to performance cores (P-cores) on hybrid CPUs.", "effect": "Better scheduling on Intel 12th+ gen", "recommendation": "Enable on Intel Alder Lake or newer", "risk": "Medium", "category": "CPU"},
                {"id": "disable_core_parking", "title": "Disable Core Parking", "description": "Prevents Windows from parking (deactivating) CPU cores. Equivalent to Disable Core Parking.reg tweaks.", "effect": "All cores immediately available for game threads", "recommendation": "Enable for gaming", "risk": "Low", "category": "CPU"},
                {"id": "timer_resolution", "title": "Timer Resolution: Max Precision", "description": "Sets Windows SystemResponsiveness to 0 for maximum multimedia timer precision.", "effect": "More precise sleep/wait calls, smoother frametimes", "recommendation": "Enable while gaming", "risk": "Low", "category": "CPU"},
                {"id": "msi_mode", "title": "MSI Mode (Message Signaled Interrupts)", "description": "Configures GPU interrupts to MSI for lower latency.", "effect": "Reduces interrupt latency", "recommendation": "Enable for NVIDIA/AMD GPUs", "risk": "Medium", "category": "CPU"},
                {"id": "disable_power_throttling", "title": "Disable Power Throttling", "description": "Removes Windows Power Throttling that limits background process performance. Based on Disable Power Throttling.reg from premium tweak packs.", "effect": "Prevents OS from throttling game-adjacent processes", "recommendation": "Enable for gaming", "risk": "Low", "category": "CPU"},
                {"id": "maintain_low_latency", "title": "Maintain Low Latency Boost", "description": "Sets SystemResponsiveness to 0 for maximum system latency reduction. Based on MaintainLowLatency-HighPerformanceBoost.REG.", "effect": "Lower system-wide input and frame latency", "recommendation": "Enable for competitive gaming", "risk": "Low", "category": "CPU"},
            ]
        },
        {
            "title": "RAM Optimization",
            "icon": "💾",
            "settings": [
                {"id": "ram_xmp", "title": "XMP / EXPO Profile", "description": "Enables your RAM's rated speed profile in BIOS.", "effect": "RAM runs at advertised speed (3200-6400+ MHz)", "recommendation": "Always enable", "risk": "Low", "category": "RAM"},
                {"id": "large_pages", "title": "Large Pages Support", "description": "Enables 4MB memory pages for reduced TLB pressure.", "effect": "Better CPU cache efficiency for large games", "recommendation": "Enable for games >8GB RAM usage", "risk": "Low", "category": "RAM"},
                {"id": "disable_superfetch", "title": "Disable SuperFetch / SysMain", "description": "Stops Windows pre-loading apps into RAM.", "effect": "More free RAM for games", "recommendation": "Disable on systems with <16GB RAM", "risk": "Low", "category": "RAM"},
            ]
        },
        {
            "title": "Windows Performance",
            "icon": "🖥️",
            "settings": [
                {"id": "power_plan_ultimate", "title": "Ultimate Performance Power Plan", "description": "Activates the hidden Ultimate Performance plan.", "effect": "Maximum CPU performance at all times", "recommendation": "Use for gaming, switch to Balanced otherwise", "risk": "Low", "category": "System"},
                {"id": "disable_notifications", "title": "Disable Notifications During Game", "description": "Suppresses all notification toasts while a game is running.", "effect": "Eliminates notification-caused frame drops", "recommendation": "Enable", "risk": "None", "category": "System"},
                {"id": "visual_effects_performance", "title": "Windows Visual Effects: Performance", "description": "Disables Aero transparency and animations in Windows.", "effect": "+2-5 FPS by freeing GPU memory", "recommendation": "Enable on low-VRAM systems", "risk": "None", "category": "System"},
                {"id": "disable_windows_defender_scan", "title": "Add Game Folder to Exclusions", "description": "Excludes game directories from real-time AV scanning.", "effect": "Eliminates anti-virus micro-stutters", "recommendation": "Enable for trusted game folders", "risk": "Medium", "category": "System"},
            ]
        },
    ]
}

PING_PAGE = {
    "id": "ping",
    "title": "NETWORK OPTIMIZER",
    "subtitle": "Achieve the lowest possible ping",
    "icon": "📡",
    "accent": "#00FFD4",
    "sections": [
        {
            "title": "DNS Optimization",
            "icon": "🌐",
            "settings": [
                {"id": "dns_cloudflare", "title": "Cloudflare DNS (1.1.1.1)", "description": "Sets DNS to Cloudflare's ultra-fast resolver.", "effect": "Faster DNS lookups, better initial connection speed", "recommendation": "Best for most regions", "risk": "None", "category": "Network"},
                {"id": "dns_google", "title": "Google DNS (8.8.8.8)", "description": "Uses Google's global DNS infrastructure.", "effect": "Reliable, consistent DNS resolution", "recommendation": "Good fallback option", "risk": "None", "category": "Network"},
                {"id": "dns_doh", "title": "DNS over HTTPS", "description": "Encrypts DNS queries to prevent ISP inspection.", "effect": "Privacy + potentially lower latency", "recommendation": "Enable for privacy", "risk": "None", "category": "Network"},
                {"id": "dns_cache_flush", "title": "Auto DNS Cache Flush", "description": "Periodically flushes stale DNS cache entries.", "effect": "Prevents connecting to outdated server IPs", "recommendation": "Enable", "risk": "None", "category": "Network"},
            ]
        },
        {
            "title": "TCP/IP Stack",
            "icon": "⚙️",
            "settings": [
                {"id": "tcp_no_delay", "title": "TCP No-Delay (Nagle Off)", "description": "Disables Nagle's algorithm so packets are sent immediately rather than buffered. Based on Disable Nagles Algorithm.reg from multiple tweak packs.", "effect": "Reduces input latency by 5-20ms", "recommendation": "Enable for gaming", "risk": "Low", "category": "Network"},
                {"id": "tcp_ack_freq", "title": "TCP ACK Frequency Optimization", "description": "Sends TCP acknowledgements more frequently.", "effect": "Better throughput on high-latency connections", "recommendation": "Enable", "risk": "Low", "category": "Network"},
                {"id": "rss_scaling", "title": "Receive-Side Scaling (RSS)", "description": "Distributes network processing across multiple CPU cores.", "effect": "Reduces network CPU bottleneck", "recommendation": "Enable on multi-core systems", "risk": "Low", "category": "Network"},
                {"id": "network_throttling_disable", "title": "Disable Network Throttling", "description": "Removes Windows multimedia network throttling.", "effect": "Full bandwidth available during gaming", "recommendation": "Enable", "risk": "None", "category": "Network"},
                {"id": "tcp_window_size", "title": "TCP Window Size Optimization", "description": "Adjusts TCP receive window for your connection speed.", "effect": "Better bandwidth utilization", "recommendation": "Auto-optimize based on speedtest", "risk": "Low", "category": "Network"},
            ]
        },
        {
            "title": "Adapter Settings",
            "icon": "🔌",
            "settings": [
                {"id": "adapter_power_save_off", "title": "Disable Adapter Power Saving", "description": "Prevents NIC from throttling to save power.", "effect": "Consistent low-latency connection", "recommendation": "Enable for wired gaming", "risk": "None", "category": "Network"},
                {"id": "interrupt_moderation_off", "title": "Disable Interrupt Moderation", "description": "NIC processes each packet immediately without batching.", "effect": "Lower latency at cost of slightly more CPU usage", "recommendation": "Enable for competitive gaming", "risk": "Low", "category": "Network"},
                {"id": "jumbo_frames", "title": "Jumbo Frames (9000 MTU)", "description": "Increases maximum packet size for less overhead.", "effect": "Better LAN throughput", "recommendation": "Only if router supports it", "risk": "Medium", "category": "Network"},
            ]
        },
        {
            "title": "Buffer Settings",
            "icon": "📦",
            "settings": [
                {"id": "socket_buffer", "title": "Socket Buffer Optimization", "description": "Tunes socket send/receive buffer sizes.", "effect": "Reduces packet loss and jitter", "recommendation": "Auto-optimize", "risk": "Low", "category": "Network"},
                {"id": "qos_priority", "title": "QoS Game Traffic Priority", "description": "Marks game UDP traffic with high DSCP priority.", "effect": "Router prioritizes game packets", "recommendation": "Enable if router supports QoS", "risk": "None", "category": "Network"},
            ]
        },
    ]
}

DELAY_PAGE = {
    "id": "delay",
    "title": "INPUT OPTIMIZER",
    "subtitle": "Zero-latency input response",
    "icon": "⌨️",
    "accent": "#9B5CF6",
    "sections": [
        {
            "title": "Mouse Settings",
            "icon": "🖱️",
            "settings": [
                {"id": "mouse_accel_off", "title": "Disable Mouse Acceleration", "description": "Removes Windows pointer acceleration (Enhance Pointer Precision).", "effect": "1:1 mouse-to-cursor mapping", "recommendation": "Always disable for FPS games", "risk": "None", "category": "Input"},
                {"id": "raw_input", "title": "Raw Input Mode", "description": "Bypasses Windows mouse API entirely.", "effect": "Removes all OS processing from mouse input", "recommendation": "Enable in game settings", "risk": "None", "category": "Input"},
                {"id": "polling_rate_1000", "title": "Mouse Polling Rate: 1000Hz", "description": "Sets mouse report rate to 1000 times per second.", "effect": "1ms input reporting interval", "recommendation": "Set in mouse software", "risk": "None", "category": "Input"},
                {"id": "usb_interrupt_priority", "title": "Mouse DataQueue Size: Optimal", "description": "Sets mouclass MouseDataQueueSize to 0x14. Based on Mouse-DataQueue.REG from premium tweak packs.", "effect": "Reduces mouse event buffering for lower click latency", "recommendation": "Enable", "risk": "Low", "category": "Input"},
            ]
        },
        {
            "title": "Keyboard Settings",
            "icon": "⌨️",
            "settings": [
                {"id": "keyboard_polling_1000", "title": "Keyboard DataQueue Size: Optimal", "description": "Sets kbdclass KeyboardDataQueueSize to 0x14. Based on Keyboard - DataQueueSize.REG from premium tweak packs.", "effect": "Reduces keyboard event buffering for faster keystroke response", "recommendation": "Enable", "risk": "None", "category": "Input"},
                {"id": "key_repeat_fast", "title": "Key Repeat Rate: Maximum", "description": "Sets Windows key repeat to maximum speed.", "effect": "Faster repeated key presses", "recommendation": "Set to personal preference", "risk": "None", "category": "Input"},
                {"id": "disable_sticky_keys", "title": "Disable Accessibility Hotkeys", "description": "Disables Sticky Keys, Filter Keys, Toggle Keys.", "effect": "Prevents accidental accessibility triggers in-game", "recommendation": "Disable while gaming", "risk": "None", "category": "Input"},
            ]
        },
        {
            "title": "Display Latency",
            "icon": "🖥️",
            "settings": [
                {"id": "vsync_off", "title": "Disable V-Sync", "description": "Removes frame synchronization with display.", "effect": "Eliminates V-Sync input lag (1-2 frame delay)", "recommendation": "Disable for competitive play", "risk": "None", "category": "Display"},
                {"id": "reflex_boost", "title": "NVIDIA Reflex + Boost", "description": "Aggressive GPU latency reduction mode.", "effect": "Up to 50% total system latency reduction", "recommendation": "Enable in supported games", "risk": "None", "category": "Display"},
                {"id": "framerate_cap", "title": "Smart FPS Cap (3-below-max)", "description": "Caps FPS slightly below monitor max for stable frametimes.", "effect": "Prevents frametime spikes, more consistent feel", "recommendation": "Cap at refreshrate - 3", "risk": "None", "category": "Display"},
            ]
        },
    ]
}

AIM_PAGE = {
    "id": "aim",
    "title": "AIM SYSTEM",
    "subtitle": "Precision tracking profiles",
    "icon": "🎯",
    "accent": "#FF2D78",
    "sections": [
        {
            "title": "Sensitivity Presets",
            "icon": "📐",
            "settings": [
                {"id": "sens_low", "title": "Low Sensitivity Profile", "description": "800 DPI, 0.3-0.5 in-game sensitivity.", "effect": "Best for tracking and long-range accuracy", "recommendation": "CS2, Valorant, R6S", "risk": "None", "category": "Aim"},
                {"id": "sens_medium", "title": "Medium Sensitivity Profile", "description": "1200-1600 DPI, balanced in-game sensitivity.", "effect": "Good balance between tracking and flicking", "recommendation": "Apex Legends, Overwatch", "risk": "None", "category": "Aim"},
                {"id": "sens_high", "title": "High Sensitivity Profile", "description": "2400-3200 DPI, high in-game sensitivity.", "effect": "Better for close-range and flick shots", "recommendation": "Battle Royale, Fortnite", "risk": "None", "category": "Aim"},
            ]
        },
        {
            "title": "Mouse Curves",
            "icon": "📈",
            "settings": [
                {"id": "curve_linear", "title": "Linear Curve (No Acceleration)", "description": "Perfect 1:1 response at all movement speeds.", "effect": "Predictable, consistent aim", "recommendation": "Best for most players", "risk": "None", "category": "Aim"},
                {"id": "curve_slight_accel", "title": "Slight Positive Acceleration", "description": "Very gentle acceleration for faster movements.", "effect": "Allows small and large movements on same sensitivity", "recommendation": "Advanced players only", "risk": "Medium", "category": "Aim"},
                {"id": "curve_natural", "title": "Natural/Ballistic Curve", "description": "Mimics the feel of professional mice pre-processing.", "effect": "More natural feeling aim movement", "recommendation": "Try if linear feels too mechanical", "risk": "Low", "category": "Aim"},
            ]
        },
        {
            "title": "Tracking Settings",
            "icon": "🔎",
            "settings": [
                {"id": "crosshair_stability", "title": "Enhanced Crosshair Stability", "description": "Optimizes system latency for crosshair responsiveness.", "effect": "More predictable crosshair behavior", "recommendation": "Enable", "risk": "None", "category": "Aim"},
                {"id": "aim_smoothness", "title": "Aim Smoothness Reduction", "description": "Disables in-engine aim smoothing/filtering.", "effect": "Raw, direct aim response", "recommendation": "Disable for competitive play", "risk": "None", "category": "Aim"},
            ]
        },
    ]
}

RECOIL_PAGE = {
    "id": "recoil",
    "title": "RECOIL CONTROL",
    "subtitle": "Master weapon recoil patterns",
    "icon": "🔫",
    "accent": "#FF6B35",
    "sections": [
        {
            "title": "Recoil Profiles",
            "icon": "🎯",
            "settings": [
                {"id": "recoil_cs2", "title": "CS2 AK-47 Recoil Pattern", "description": "Optimized settings for CS2 AK-47 spray control.", "effect": "Better recoil compensation", "recommendation": "Practice in aim training first", "risk": "None", "category": "Recoil"},
                {"id": "recoil_valorant", "title": "Valorant Vandal Pattern", "description": "Mouse settings tuned for Valorant Vandal recoil.", "effect": "More consistent Vandal sprays", "recommendation": "Combine with low sensitivity", "risk": "None", "category": "Recoil"},
                {"id": "recoil_apex", "title": "Apex Legends R-301 Pattern", "description": "Settings for Apex R-301 recoil control.", "effect": "Easier full-auto control", "recommendation": "Enable for beginners", "risk": "None", "category": "Recoil"},
            ]
        },
        {
            "title": "Sensitivity Presets",
            "icon": "📊",
            "settings": [
                {"id": "recoil_sens_comp", "title": "Recoil Compensation Sensitivity", "description": "Slightly lower DPI for more precise recoil control.", "effect": "Finer control of muzzle climb compensation", "recommendation": "800-1000 DPI for spray control", "risk": "None", "category": "Recoil"},
            ]
        },
    ]
}

BLOOM_PAGE = {
    "id": "bloom",
    "title": "BLOOM & VISIBILITY",
    "subtitle": "Maximum visual clarity",
    "icon": "👁️",
    "accent": "#FFB800",
    "sections": [
        {
            "title": "Bloom Profiles",
            "icon": "💡",
            "settings": [
                {"id": "bloom_off", "title": "Disable Bloom Effects", "description": "Removes bloom post-processing from supported games.", "effect": "Cleaner sight picture, easier target tracking", "recommendation": "Disable for competitive play", "risk": "None", "category": "Bloom"},
                {"id": "motion_blur_off", "title": "Disable Motion Blur", "description": "Removes motion blur from camera and objects.", "effect": "Cleaner visuals during movement", "recommendation": "Always disable for FPS games", "risk": "None", "category": "Bloom"},
                {"id": "chromatic_aberration_off", "title": "Disable Chromatic Aberration", "description": "Removes color fringing effect.", "effect": "Sharper image", "recommendation": "Disable", "risk": "None", "category": "Bloom"},
            ]
        },
        {
            "title": "Visibility Profiles",
            "icon": "🔍",
            "settings": [
                {"id": "digital_vibrance", "title": "Digital Vibrance +60%", "description": "Increases color saturation via GPU driver.", "effect": "Enemies and items stand out more", "recommendation": "60-80% for competitive games", "risk": "None", "category": "Visibility"},
                {"id": "gamma_adjust", "title": "Gamma Brightness Adjustment", "description": "Brightens dark areas without washing out bright areas.", "effect": "Better visibility in dark map areas", "recommendation": "2.3-2.5 gamma", "risk": "None", "category": "Visibility"},
                {"id": "clarity_filter", "title": "Image Sharpness Filter", "description": "Applies GPU-level sharpening filter.", "effect": "Crisper textures and edges", "recommendation": "30-50% sharpness", "risk": "None", "category": "Visibility"},
            ]
        },
    ]
}

SYSTEM_PAGE = {
    "id": "system",
    "title": "SYSTEM OPTIMIZER",
    "subtitle": "Windows performance tuning",
    "icon": "🖥️",
    "accent": "#00FFD4",
    "sections": [
        {
            "title": "Windows Optimizations",
            "icon": "🪟",
            "settings": [
                {"id": "telemetry_off", "title": "Disable Telemetry", "description": "Stops Windows from sending diagnostic data to Microsoft.", "effect": "Reduced background network and CPU usage", "recommendation": "Enable for privacy and performance", "risk": "None", "category": "System"},
                {"id": "cortana_off", "title": "Disable Cortana", "description": "Disables the Cortana search assistant.", "effect": "Frees RAM and CPU on startup", "recommendation": "Disable if unused", "risk": "None", "category": "System"},
                {"id": "search_index_off", "title": "Disable Search Indexing", "description": "Stops Windows Search from indexing files.", "effect": "Reduces disk I/O during gaming", "recommendation": "Disable on HDD systems", "risk": "Low", "category": "System"},
                {"id": "windows_update_delay", "title": "Pause Windows Updates", "description": "Pauses automatic Windows updates.", "effect": "Prevents update-related restarts/slowdowns", "recommendation": "Re-enable weekly to stay patched", "risk": "Medium", "category": "System"},
                {"id": "fast_startup", "title": "Fast Startup Mode", "description": "Hybrid shutdown that preserves kernel session.", "effect": "2-3x faster boot time", "recommendation": "Enable", "risk": "Low", "category": "System"},
            ]
        },
        {
            "title": "Services",
            "icon": "⚙️",
            "settings": [
                {"id": "svc_print_spooler", "title": "Disable Print Spooler", "description": "Disables Windows printing service.", "effect": "Frees a small amount of RAM", "recommendation": "Disable if no printer", "risk": "None", "category": "System"},
                {"id": "svc_fax", "title": "Disable Fax Service", "description": "Disables the Windows fax service.", "effect": "Minor system cleanup", "recommendation": "Safe to disable", "risk": "None", "category": "System"},
                {"id": "svc_sysmain", "title": "Disable SysMain (SuperFetch)", "description": "Disables RAM pre-loading service.", "effect": "More free RAM for games", "recommendation": "Disable with SSD systems", "risk": "Low", "category": "System"},
                {"id": "svc_bits", "title": "Disable BITS Service", "description": "Stops Background Intelligent Transfer Service.", "effect": "Prevents background downloads eating bandwidth", "recommendation": "Enable only during gaming", "risk": "Low", "category": "System"},
            ]
        },
        {
            "title": "Registry Tweaks",
            "icon": "🔑",
            "settings": [
                {"id": "reg_irq8_priority", "title": "IRQ8 Priority Boost", "description": "Raises IRQ8 (system timer) priority in PriorityControl registry. Equivalent to IRQ8Priority.reg found in HyperTweaks, Risxn, and other packs.", "effect": "More precise timer resolution and system responsiveness", "recommendation": "Enable for gaming", "risk": "Low", "category": "System"},
                {"id": "disable_power_throttling", "title": "Disable Power Throttling", "description": "Sets PowerThrottlingOff=1 in the OS power throttling control. Matches Disable Power Throttling.reg present in AlphaWolf, Vynla, Aphrodite and more.", "effect": "Prevents OS from throttling game-adjacent CPU processes", "recommendation": "Enable for gaming", "risk": "Low", "category": "System"},
                {"id": "maintain_low_latency", "title": "Maintain Low Latency Boost", "description": "Sets SystemResponsiveness to 0 (maximum) for network and timer subsystems. Based on MaintainLowLatency-HighPerformanceBoost.REG.", "effect": "Reduces audio/game scheduling latency system-wide", "recommendation": "Enable for competitive gaming", "risk": "Low", "category": "System"},
                {"id": "reg_no_low_disk", "title": "Disable Low Disk Space Check", "description": "Removes periodic disk space notification from Explorer.", "effect": "Minor performance improvement", "recommendation": "Enable", "risk": "None", "category": "System"},
            ]
        },
        {
            "title": "Memory Management",
            "icon": "💾",
            "settings": [
                {"id": "pagefile_optimize", "title": "Optimize Pagefile Size", "description": "Sets pagefile to 1.5x RAM for best performance.", "effect": "Stable memory management", "recommendation": "Set automatically", "risk": "Low", "category": "System"},
                {"id": "clear_standby_ram", "title": "Auto Clear Standby RAM", "description": "Periodically clears RAM in standby state.", "effect": "More free RAM available for games", "recommendation": "Enable", "risk": "Low", "category": "System"},
                {"id": "large_system_cache_off", "title": "Optimize for Programs (not cache)", "description": "Adjusts memory manager to prioritize programs over file cache.", "effect": "Games get more direct RAM access", "recommendation": "Enable", "risk": "Low", "category": "System"},
            ]
        },
    ]
}

GAME_PAGE = {
    "id": "game",
    "title": "GAME PROFILES",
    "subtitle": "Per-game optimized configurations",
    "icon": "🎮",
    "accent": "#9B5CF6",
    "sections": [
        {
            "title": "Fortnite",
            "icon": "🌀",
            "settings": [
                {"id": "fn_dx12", "title": "Fortnite: DirectX 12 Mode", "description": "Enables DX12 for better multi-core GPU utilization in Fortnite.", "effect": "+10-20% FPS on high-end systems", "recommendation": "Use with RTX 3000+ or RX 6000+", "risk": "Low", "category": "Fortnite"},
                {"id": "fn_nanite_off", "title": "Disable Nanite Visualization", "description": "Reduces Unreal Engine 5 Nanite overhead.", "effect": "+15% FPS on mid-range systems", "recommendation": "Enable on low-mid GPUs", "risk": "None", "category": "Fortnite"},
                {"id": "fn_shadows_off", "title": "Shadows: Off", "description": "Disables shadow rendering in Fortnite.", "effect": "+20-30 FPS", "recommendation": "Competitive players", "risk": "None", "category": "Fortnite"},
                {"id": "fn_config_boost", "title": "GameUserSettings.ini Boost", "description": "Applies competitive .ini optimizations.", "effect": "Maximum competitive performance", "recommendation": "Apply before ranked sessions", "risk": "Low", "category": "Fortnite"},
            ]
        },
        {
            "title": "Valorant",
            "icon": "🔺",
            "settings": [
                {"id": "val_low_latency", "title": "Valorant: Low Latency Mode", "description": "Configures Valorant for minimum system latency.", "effect": "-15ms average system latency", "recommendation": "Enable for ranked", "risk": "None", "category": "Valorant"},
                {"id": "val_graphics_opt", "title": "Valorant: Competitive Graphics Config", "description": "Sets all graphics to minimum for maximum FPS.", "effect": "400+ FPS on high-end systems", "recommendation": "Use for ranked play", "risk": "None", "category": "Valorant"},
                {"id": "val_multithreaded", "title": "Multithreaded Rendering: On", "description": "Enables CPU multithreading for Valorant renderer.", "effect": "+20% FPS on 6+ core CPUs", "recommendation": "Enable", "risk": "None", "category": "Valorant"},
            ]
        },
        {
            "title": "CS2",
            "icon": "💣",
            "settings": [
                {"id": "cs2_launchops", "title": "CS2 Launch Options Pack", "description": "Applies -threads, -high, -nojoy and more launch options.", "effect": "Better CPU utilization and lower latency", "recommendation": "Apply and restart Steam", "risk": "None", "category": "CS2"},
                {"id": "cs2_rate", "title": "CS2 Network Rate Optimization", "description": "Sets rate, cmdrate, updaterate to maximum.", "effect": "More server updates per second", "recommendation": "Enable on fast internet", "risk": "None", "category": "CS2"},
                {"id": "cs2_sub_tick", "title": "Sub-Tick Optimization", "description": "Optimizes CS2 sub-tick system settings.", "effect": "More accurate hit registration", "recommendation": "Enable", "risk": "None", "category": "CS2"},
            ]
        },
        {
            "title": "Apex Legends",
            "icon": "🔥",
            "settings": [
                {"id": "apex_video_config", "title": "Apex: Competitive Video Config", "description": "Applies low-settings video config for Apex.", "effect": "Stable 100+ FPS", "recommendation": "Use for ranked matches", "risk": "None", "category": "Apex"},
                {"id": "apex_paksound", "title": "Disable Apex Origin Overlay", "description": "Removes the Origin/EA overlay from Apex.", "effect": "Slightly lower RAM usage", "recommendation": "Disable", "risk": "None", "category": "Apex"},
            ]
        },
        {
            "title": "Call of Duty",
            "icon": "💥",
            "settings": [
                {"id": "cod_taa_off", "title": "COD: Disable TAA", "description": "Turns off Temporal Anti-Aliasing in Modern Warfare.", "effect": "Sharper image, more FPS", "recommendation": "Use SMAA instead", "risk": "None", "category": "CoD"},
                {"id": "cod_texture_streaming", "title": "COD: On-Demand Texture Streaming", "description": "Disables texture streaming to prevent hitching.", "effect": "Fewer texture pop-in stutters", "recommendation": "Disable on fast SSDs", "risk": "None", "category": "CoD"},
            ]
        },
        {
            "title": "Rainbow Six Siege",
            "icon": "🌈",
            "settings": [
                {"id": "r6_vulkan", "title": "R6: Vulkan API", "description": "Switches Siege to Vulkan render API.", "effect": "+20% FPS, better multi-core usage", "recommendation": "Enable on AMD GPUs", "risk": "Low", "category": "R6"},
                {"id": "r6_render_scaling", "title": "R6: Render Scaling 100%", "description": "Locks render resolution to native.", "effect": "Clearest image quality", "recommendation": "Use with high FPS headroom", "risk": "None", "category": "R6"},
            ]
        },
        {
            "title": "PUBG",
            "icon": "🪂",
            "settings": [
                {"id": "pubg_dx12", "title": "PUBG: DirectX 12", "description": "Enables DX12 in PUBG for multi-core benefits.", "effect": "+15% FPS", "recommendation": "Enable on modern hardware", "risk": "Low", "category": "PUBG"},
            ]
        },
    ]
}

BIOS_PAGE = {
    "id": "bios",
    "title": "BIOS OPTIMIZER",
    "subtitle": "Hardware-level performance settings",
    "icon": "🔬",
    "accent": "#00C8FF",
    "sections": [
        {
            "title": "CPU Settings",
            "icon": "🔧",
            "settings": [
                {"id": "bios_pbo", "title": "Precision Boost Overdrive (PBO)", "description": "Enables AMD's automatic CPU overclocking algorithm.", "effect": "+10-20% multi-core performance on Ryzen", "recommendation": "Enable on AMD systems", "risk": "Medium", "category": "BIOS"},
                {"id": "bios_smt", "title": "SMT / Hyperthreading", "description": "Simultaneous Multi-Threading for logical core doubling.", "effect": "Better multi-threaded performance", "recommendation": "Enable (disable only for specific competitive games)", "risk": "Low", "category": "BIOS"},
                {"id": "bios_cpu_power", "title": "CPU Power Limits: Unlocked", "description": "Removes power limits (PL1/PL2/TDP) on Intel CPUs.", "effect": "Sustained boost clocks without throttling", "recommendation": "Enable with adequate cooling", "risk": "Medium", "category": "BIOS"},
            ]
        },
        {
            "title": "RAM Settings",
            "icon": "💾",
            "settings": [
                {"id": "bios_expo", "title": "Enable EXPO Profile", "description": "AMD's Extended Profiles for Overclocking (EXPO).", "effect": "RAM runs at rated DDR5 speed", "recommendation": "Enable on AM5 platform", "risk": "Low", "category": "BIOS"},
                {"id": "bios_xmp", "title": "Enable XMP Profile", "description": "Intel's eXtreme Memory Profile for rated DDR4/DDR5 speed.", "effect": "RAM at advertised MHz", "recommendation": "Always enable", "risk": "Low", "category": "BIOS"},
                {"id": "bios_ram_timings", "title": "Tight Memory Timings", "description": "Manually tightened CAS latency and sub-timings.", "effect": "+5-15% memory bandwidth", "recommendation": "Advanced users only", "risk": "High", "category": "BIOS"},
            ]
        },
        {
            "title": "Power Settings",
            "icon": "⚡",
            "settings": [
                {"id": "bios_c_states_off", "title": "Disable C-States", "description": "Prevents CPU from entering sleep states.", "effect": "Instant CPU response, slightly higher idle power", "recommendation": "Disable for competitive gaming rigs", "risk": "Low", "category": "BIOS"},
                {"id": "bios_spread_spectrum", "title": "Disable Spread Spectrum", "description": "Removes frequency spreading used for EMI reduction.", "effect": "More stable overclocking", "recommendation": "Disable when overclocking", "risk": "Low", "category": "BIOS"},
            ]
        },
    ]
}

PLAYSTATION_PAGE = {
    "id": "playstation",
    "title": "PLAYSTATION HUB",
    "subtitle": "PS4 & PS5 optimization",
    "icon": "🎮",
    "accent": "#0070D1",
    "sections": [
        {
            "title": "PS5 Settings",
            "icon": "🔵",
            "settings": [
                {"id": "ps5_performance_mode", "title": "PS5: Performance Mode", "description": "Sets PS5 to prioritize FPS over resolution.", "effect": "60+ FPS in most games vs 30 FPS quality mode", "recommendation": "Always use for competitive games", "risk": "None", "category": "PS5"},
                {"id": "ps5_vrd", "title": "PS5: Variable Rate Display", "description": "Enables VRR on compatible 4K TVs.", "effect": "Smoother framerate during drops", "recommendation": "Enable with HDMI 2.1 TV", "risk": "None", "category": "PS5"},
                {"id": "ps5_120hz", "title": "PS5: 120Hz Output", "description": "Enables 120Hz video output for supported games.", "effect": "2x smoother gameplay where supported", "recommendation": "Enable with 120Hz display", "risk": "None", "category": "PS5"},
                {"id": "ps5_rest_mode_off", "title": "Disable Rest Mode", "description": "Disables PS5 automatic rest mode.", "effect": "Prevents unexpected mid-session shut off", "recommendation": "Disable during long sessions", "risk": "None", "category": "PS5"},
            ]
        },
        {
            "title": "PS4 Settings",
            "icon": "🎮",
            "settings": [
                {"id": "ps4_boost_mode", "title": "PS4 Pro: Boost Mode", "description": "Enables PS4 Pro's boost mode for legacy games.", "effect": "Better FPS in older PS4 games", "recommendation": "Enable on PS4 Pro", "risk": "Low", "category": "PS4"},
                {"id": "ps4_supersampling", "title": "PS4 Pro: Supersampling", "description": "Renders at 4K and downsamples to 1080p.", "effect": "Sharper image quality on 1080p TVs", "recommendation": "Enable for single player games", "risk": "None", "category": "PS4"},
            ]
        },
        {
            "title": "Controller Profiles",
            "icon": "🕹️",
            "settings": [
                {"id": "ps_controller_fps", "title": "FPS Controller Layout", "description": "Optimized button mapping for FPS games.", "effect": "Better control scheme for shooters", "recommendation": "Use for COD/Fortnite/Apex", "risk": "None", "category": "Controller"},
                {"id": "ps_deadzone_min", "title": "Minimum Deadzone", "description": "Reduces analog stick deadzone to minimum.", "effect": "More precise stick movement", "recommendation": "Calibrate per controller", "risk": "None", "category": "Controller"},
                {"id": "ps_trigger_sensitivity", "title": "Adaptive Trigger Sensitivity", "description": "Adjusts DualSense adaptive trigger resistance.", "effect": "Consistent trigger feel", "recommendation": "Personal preference", "risk": "None", "category": "Controller"},
            ]
        },
    ]
}

XBOX_PAGE = {
    "id": "xbox",
    "title": "XBOX HUB",
    "subtitle": "Xbox Series optimization",
    "icon": "🟢",
    "accent": "#107C10",
    "sections": [
        {
            "title": "Xbox Series X",
            "icon": "🟩",
            "settings": [
                {"id": "xsx_fidelity_120", "title": "Series X: 120fps Mode", "description": "Forces supported games to run at 120fps.", "effect": "2x smoother gameplay", "recommendation": "Enable with 120Hz display", "risk": "None", "category": "Xbox"},
                {"id": "xsx_vrd", "title": "Xbox VRR / FreeSync", "description": "Enables variable refresh rate on Xbox.", "effect": "Tear-free gaming at variable FPS", "recommendation": "Enable with compatible display", "risk": "None", "category": "Xbox"},
                {"id": "xsx_allm", "title": "Auto Low Latency Mode (ALLM)", "description": "Automatically triggers TV game mode.", "effect": "Lowest possible display latency", "recommendation": "Enable", "risk": "None", "category": "Xbox"},
            ]
        },
        {
            "title": "Xbox Series S",
            "icon": "⬜",
            "settings": [
                {"id": "xss_performance_target", "title": "Series S: Performance Target Mode", "description": "Developer performance mode for higher FPS.", "effect": "60 FPS in more games", "recommendation": "Enable where supported", "risk": "None", "category": "Xbox"},
                {"id": "xss_resolution_1440", "title": "Series S: 1440p Output", "description": "Native 1440p output for sharper image.", "effect": "Cleaner image vs 1080p upscale", "recommendation": "Enable with 1440p monitor", "risk": "None", "category": "Xbox"},
            ]
        },
        {
            "title": "Controller Profiles",
            "icon": "🕹️",
            "settings": [
                {"id": "xbox_controller_fps", "title": "FPS Optimized Layout", "description": "Remapped controls for FPS games on Xbox.", "effect": "Better shooting ergonomics", "recommendation": "COD, Apex, Halo", "risk": "None", "category": "Controller"},
                {"id": "xbox_deadzone_min", "title": "Minimum Stick Deadzone", "description": "Reduces Xbox controller stick deadzone.", "effect": "More responsive stick input", "recommendation": "Calibrate with Accessories app", "risk": "None", "category": "Controller"},
                {"id": "xbox_trigger_rumble", "title": "Trigger Haptic Intensity", "description": "Adjusts Xbox controller trigger rumble strength.", "effect": "Better haptic feedback", "recommendation": "Personal preference", "risk": "None", "category": "Controller"},
            ]
        },
    ]
}

MACROS_PAGE = {
    "id": "macros",
    "title": "MACRO STUDIO",
    "subtitle": "Advanced input automation",
    "icon": "🤖",
    "accent": "#FF2D78",
    "sections": [
        {
            "title": "Keyboard Macros",
            "icon": "⌨️",
            "settings": [
                {"id": "macro_rapid_fire", "title": "Rapid Fire Toggle", "description": "Creates a rapid-fire key binding.", "effect": "Automatic key repeat at defined interval", "recommendation": "Check game ToS before using", "risk": "Medium", "category": "Macro"},
                {"id": "macro_crouch_slide", "title": "Crouch-Slide Macro", "description": "Sprint + crouch timed for slide mechanics.", "effect": "Consistent sliding in games with slide mechanics", "recommendation": "Fortnite, Warzone", "risk": "Low", "category": "Macro"},
                {"id": "macro_build_edit", "title": "Build-Edit Combo (Fortnite)", "description": "Optimized key sequence for Fortnite build-edit.", "effect": "Faster build-edit combinations", "recommendation": "Practice timing", "risk": "None", "category": "Macro"},
            ]
        },
        {
            "title": "Mouse Macros",
            "icon": "🖱️",
            "settings": [
                {"id": "macro_burst_click", "title": "Burst Click Pattern", "description": "Timed click bursts for games with burst mechanics.", "effect": "Consistent burst timing", "recommendation": "CS2 burst fire weapons", "risk": "Medium", "category": "Macro"},
                {"id": "macro_drag_click", "title": "Drag Click Assist", "description": "Optimizes settings for drag-clicking technique.", "effect": "Higher CPS in supported scenarios", "recommendation": "Practice technique", "risk": "None", "category": "Macro"},
            ]
        },
        {
            "title": "Advanced Profiles",
            "icon": "🧠",
            "settings": [
                {"id": "macro_profile_fps", "title": "FPS Macro Profile", "description": "Complete macro set optimized for FPS games.", "effect": "All FPS-relevant macros pre-configured", "recommendation": "Apply for FPS sessions", "risk": "Low", "category": "Macro"},
                {"id": "macro_profile_br", "title": "Battle Royale Profile", "description": "Macros tuned for Battle Royale games.", "effect": "Optimized for BR building and movement", "recommendation": "Fortnite, PUBG, Apex", "risk": "Low", "category": "Macro"},
                {"id": "macro_profile_moba", "title": "MOBA Macro Profile", "description": "Smart item activate and combo macros.", "effect": "Faster reaction combos", "recommendation": "League of Legends, Dota 2", "risk": "None", "category": "Macro"},
            ]
        },
    ]
}

ALL_PAGES = [FPS_PAGE, PING_PAGE, DELAY_PAGE, AIM_PAGE, RECOIL_PAGE,
             BLOOM_PAGE, SYSTEM_PAGE, GAME_PAGE, BIOS_PAGE,
             PLAYSTATION_PAGE, XBOX_PAGE, MACROS_PAGE]

PAGE_MAP = {p["id"]: p for p in ALL_PAGES}
