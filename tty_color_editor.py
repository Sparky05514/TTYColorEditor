#!/usr/bin/env python3
import curses
import sys
import os
import json
import re
import subprocess

# Standard Linux Console Colors (0-15)

# Standard Linux Console Colors (0-15) - Default Fallback

# Standard Linux Console Colors (0-15) - Default Fallback
DEFAULT_COLORS = [
    "000000", "AA0000", "00AA00", "AA5500", "0000AA", "AA00AA", "00AAAA", "AAAAAA",
    "555555", "FF5555", "55FF55", "FFFF55", "5555FF", "FF55FF", "55FFFF", "FFFFFF"
]

COLOR_NAMES = [
    "Black", "Red", "Green", "Brown/Yellow", "Blue", "Magenta", "Cyan", "Light Gray",
    "Dark Gray", "Light Red", "Light Green", "Light Yellow", "Light Blue", "Light Magenta", "Light Cyan", "White"
]

PRESETS = {
    "Default": DEFAULT_COLORS,
    "Matrix": [
        "000000", "FF0000", "00CC00", "FFFF00", "0000FF", "FF00FF", "00FFFF", "00FF00",
        "555555", "FF5555", "55FF55", "FFFF55", "5555FF", "FF55FF", "55FFFF", "CCFFCC"
    ],
    "Dracula": [
        "21222C", "FF5555", "50FA7B", "F1FA8C", "BD93F9", "FF79C6", "8BE9FD", "F8F8F2",
        "6272A4", "FF6E6E", "69FF94", "FFFFA5", "D6ACFF", "FF92DF", "A4FFFF", "FFFFFF"
    ],
    "Gruvbox": [
        "282828", "CC241D", "98971A", "D79921", "458588", "B16286", "689D6A", "A89984",
        "928374", "FB4934", "B8BB26", "FABD2F", "83A598", "D3869B", "8EC07C", "EBDBB2"
    ],
    "Solarized": [
        "073642", "DC322F", "859900", "B58900", "268BD2", "D33682", "2AA198", "EEE8D5",
        "002B36", "CB4B16", "586E75", "657B83", "839496", "6C71C4", "93A1A1", "FDF6E3"
    ],
    "Catppuccin": [
        "494D64", "ED8796", "A6DA95", "F5A97F", "8AADF4", "F5BDE6", "8BD5CA", "CAD3F5",
        "494D64", "ED8796", "A6DA95", "F5A97F", "8AADF4", "F5BDE6", "8BD5CA", "CAD3F5"
    ],
    "Nord": [
        "2E3440", "BF616A", "A3BE8C", "EBCB8B", "81A1C1", "B48EAD", "88C0D0", "E5E9F0",
        "4C566A", "BF616A", "A3BE8C", "EBCB8B", "81A1C1", "B48EAD", "8FBCBB", "ECEFF4"
    ],
    "Rosé Pine": [
        "26233A", "EB6F92", "31748F", "F6C177", "9CCFD8", "C4A7E7", "EBBCBA", "E0DEF4",
        "6E6A86", "EB6F92", "31748F", "F6C177", "9CCFD8", "C4A7E7", "EBBCBA", "E0DEF4"
    ],
    "Tokyo Night": [
        "1A1B26", "F7768E", "9ECE6A", "E0AF68", "7AA2F7", "BB9AF7", "7DCFFF", "C0CAF5",
        "414868", "F7768E", "9ECE6A", "E0AF68", "7AA2F7", "BB9AF7", "7DCFFF", "C0CAF5"
    ]
}

USAGE_HINTS = [
    "Background", "Archives/Err", "Executables", "Pipes/Devs", 
    "Directories", "Images", "Symlinks", "Text/Normal",
    "Comments", "Bold Red", "Bold Green", "Bold Yellow",
    "Bold Blue", "Bold Magenta", "Bold Cyan", "Bold White"
]

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return f"{r:02X}{g:02X}{b:02X}"

def scale_color(hex_color, brightness):
    r, g, b = hex_to_rgb(hex_color)
    r = max(0, min(255, int(r * brightness)))
    g = max(0, min(255, int(g * brightness)))
    b = max(0, min(255, int(b * brightness)))
    return rgb_to_hex(r, g, b)

def apply_color(index, hex_color):
    if not (0 <= index <= 15):
        return
    sys.stdout.write(f"\033]P{index:X}{hex_color}")
    sys.stdout.flush()

def get_fonts():
    font_dir = "/usr/share/consolefonts"
    if not os.path.exists(font_dir):
        return []
    fonts = [f for f in os.listdir(font_dir) if f.endswith(".psf.gz") or f.endswith(".psf")]
    return sorted(fonts)

def apply_font(font_name):
    try:
        subprocess.run(["setfont", font_name], check=True)
    except Exception:
        pass

def apply_cursor(shape_idx, blink):
    # Linux console cursor escape sequences: \033[?Xc
    # 0: default, 1: block, 2: underline, 3: lower third, 4: lower half, 5: two thirds, 6: full block
    # Blink is usually controlled by setterm
    try:
        shape_seq = f"\033[?{shape_idx}c"
        sys.stdout.write(shape_seq)
        sys.stdout.flush()
        blink_cmd = "on" if blink else "off"
        subprocess.run(["setterm", "--blink", blink_cmd], check=False)
    except Exception:
        pass

class ColorEditor:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        curses.start_color()
        if curses.has_colors():
             curses.use_default_colors()
             for i in range(1, 17):
                 try: curses.init_pair(i, i-1, -1)
                 except: pass

        self.base_colors = list(DEFAULT_COLORS)
        self.colors = list(DEFAULT_COLORS)
        self.brightness = 1.0
        self.current_selection = 0
        
        # State: 'LIST', 'EDIT', 'PRESETS', 'INSTALL', 'FONTS', 'CURSOR'
        self.state = 'LIST'
        
        # Edit vars
        self.edit_rgb = [0, 0, 0]
        self.edit_channel_idx = 0
        
        # Preset vars
        self.preset_list = list(PRESETS.keys())
        self.preset_idx = 0

        # Font vars
        self.fonts = get_fonts()
        self.font_idx = 0
        self.current_font = "Default"

        # Cursor vars
        self.cursor_shapes = ["Default", "Block", "Underline", "Lower Third", "Lower Half", "Two Thirds", "Full Block"]
        self.cursor_shape_idx = 0
        self.cursor_blink = True
        self.cursor_edit_idx = 0
        
        self.message = "ARROWS:Move | ENTER:Edit | S:Save | P:Presets | F:Fonts | C:Cursor | I:Install | Q:Quit"

    def run(self):
        while True:
            self.draw_ui()
            key = self.stdscr.getch()
            
            if self.state == 'LIST':
                if key in [ord('q'), ord('Q')]: break
                elif key == curses.KEY_UP: self.current_selection = (self.current_selection - 1) % 16
                elif key == curses.KEY_DOWN: self.current_selection = (self.current_selection + 1) % 16
                elif key in [ord('\n'), curses.KEY_ENTER]: self.enter_edit_mode()
                elif key in [ord('s'), ord('S')]: self.save_theme_dialog()
                elif key in [ord('p'), ord('P')]: self.state = 'PRESETS'; self.message = "Select Preset (ENTER to apply, ESC to cancel)"
                elif key in [ord('f'), ord('F')]: self.state = 'FONTS'; self.message = "Select Font (ENTER to apply, ESC to cancel)"
                elif key in [ord('c'), ord('C')]: self.state = 'CURSOR'; self.message = "UD: Option | LR: Toggle | ESC: Back"
                elif key in [ord('i'), ord('I')]: self.state = 'INSTALL'; self.message = "I: Install to .bashrc | U: Uninstall | ESC: Cancel"
                elif key == ord('['): self.adjust_brightness(-0.05)
                elif key == ord(']'): self.adjust_brightness(0.05)
            
            elif self.state == 'EDIT':
                if key == 27: self.state = 'LIST'; self.reset_msg()
                elif key in [ord('\n'), curses.KEY_ENTER]: self.state = 'LIST'; self.reset_msg()
                elif key == curses.KEY_UP: self.edit_channel_idx = (self.edit_channel_idx - 1) % 3
                elif key == curses.KEY_DOWN: self.edit_channel_idx = (self.edit_channel_idx + 1) % 3
                elif key == curses.KEY_LEFT: self.adjust_color(-1)
                elif key == curses.KEY_RIGHT: self.adjust_color(1)
            
            elif self.state == 'PRESETS':
                if key == 27: self.state = 'LIST'; self.reset_msg()
                elif key == curses.KEY_UP: self.preset_idx = (self.preset_idx - 1) % len(self.preset_list)
                elif key == curses.KEY_DOWN: self.preset_idx = (self.preset_idx + 1) % len(self.preset_list)
                elif key in [ord('\n'), curses.KEY_ENTER]: self.apply_preset(self.preset_list[self.preset_idx]); self.state = 'LIST'; self.reset_msg()

            elif self.state == 'FONTS':
                if key == 27: self.state = 'LIST'; self.reset_msg()
                elif key == curses.KEY_UP: self.font_idx = (self.font_idx - 1) % len(self.fonts)
                elif key == curses.KEY_DOWN: self.font_idx = (self.font_idx + 1) % len(self.fonts)
                elif key in [ord('\n'), curses.KEY_ENTER]: 
                    self.current_font = self.fonts[self.font_idx]
                    apply_font(self.current_font)
                    self.state = 'LIST'; self.reset_msg()

            elif self.state == 'CURSOR':
                if key == 27: self.state = 'LIST'; self.reset_msg()
                elif key == curses.KEY_UP: self.cursor_edit_idx = (self.cursor_edit_idx - 1) % 2
                elif key == curses.KEY_DOWN: self.cursor_edit_idx = (self.cursor_edit_idx + 1) % 2
                elif key in [curses.KEY_LEFT, curses.KEY_RIGHT]:
                    if self.cursor_edit_idx == 0:
                        delta = 1 if key == curses.KEY_RIGHT else -1
                        self.cursor_shape_idx = (self.cursor_shape_idx + delta) % len(self.cursor_shapes)
                    else:
                        self.cursor_blink = not self.cursor_blink
                    apply_cursor(self.cursor_shape_idx, self.cursor_blink)

            elif self.state == 'INSTALL':
                if key == 27: self.state = 'LIST'; self.reset_msg()
                elif key in [ord('i'), ord('I')]: self.install_permanent()
                elif key in [ord('u'), ord('U')]: self.uninstall_permanent()

    def reset_msg(self):
        self.message = "ARROWS:Move | ENTER:Edit | S:Save | P:Presets | F:Fonts | C:Cursor | [ ]:Bright | Q:Quit"

    def enter_edit_mode(self):
        self.state = 'EDIT'
        self.message = "UD: Channel | LR: Adjust | ENTER: Done"
        r, g, b = hex_to_rgb(self.base_colors[self.current_selection])
        self.edit_rgb = [r, g, b]
        self.edit_channel_idx = 0

    def adjust_color(self, delta):
        self.edit_rgb[self.edit_channel_idx] = max(0, min(255, self.edit_rgb[self.edit_channel_idx] + delta))
        new_hex = rgb_to_hex(*self.edit_rgb)
        self.base_colors[self.current_selection] = new_hex
        self.colors[self.current_selection] = scale_color(new_hex, self.brightness)
        apply_color(self.current_selection, self.colors[self.current_selection])
        
    def adjust_brightness(self, delta):
        self.brightness = max(0.1, min(2.0, self.brightness + delta))
        for i in range(16):
            self.colors[i] = scale_color(self.base_colors[i], self.brightness)
            apply_color(i, self.colors[i])

    def apply_preset(self, name):
        if name in PRESETS:
            self.base_colors = list(PRESETS[name])
            for i in range(16):
                self.colors[i] = scale_color(self.base_colors[i], self.brightness)
                apply_color(i, self.colors[i])
            self.message = f"Applied preset: {name}"

    def draw_bar(self, y, x, value, label, is_selected):
        filled_len = int((value / 255.0) * 20)
        bar_str = "█" * filled_len + "░" * (20 - filled_len)
        prefix = "> " if is_selected else "  "
        attr = curses.A_BOLD if is_selected else curses.A_NORMAL
        self.stdscr.addstr(y, x, f"{prefix}{label} [{bar_str}] {value:3}", attr)

    def draw_ui(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        self.stdscr.addstr(1, (width - 25) // 2, f"TTY Color Editor (B:{self.brightness:.2f})", curses.A_BOLD)

        # -- LEFT PANEL (List) --
        start_y = 3
        for i in range(16):
            if start_y + i >= height - 2: break
            is_cursor = (i == self.current_selection) and (self.state == 'LIST')
            is_active_edit = (i == self.current_selection) and (self.state == 'EDIT')
            prefix = " >" if is_cursor else (" *" if is_active_edit else "  ")
            color_hex = self.colors[i]
            base_hex = self.base_colors[i]
            attr = curses.A_REVERSE if (is_cursor or is_active_edit) else curses.A_NORMAL
            
            # Add label hint
            hint = f"({USAGE_HINTS[i]})"
            self.stdscr.addstr(start_y + i, 2, f"{prefix} {i:<2} {COLOR_NAMES[i][:10]:<10} #{color_hex} {hint}", attr)
            
            if curses.has_colors():
                 try: self.stdscr.addstr(start_y + i, 50, "█", curses.color_pair(i+1) | curses.A_BOLD)
                 except: pass

        # -- RIGHT PANEL (Context Dependent) --
        detail_x = 35
        detail_y = 5
        
        if self.state == 'EDIT':
            self.stdscr.addstr(detail_y, detail_x, f"EDIT COLOR {self.current_selection}", curses.A_UNDERLINE)
            try:
                for r in range(3): self.stdscr.addstr(detail_y + 2 + r, detail_x, "██████████", curses.color_pair(self.current_selection+1))
            except: pass
            
            self.draw_bar(detail_y+6, detail_x, self.edit_rgb[0], "R", self.edit_channel_idx==0)
            self.draw_bar(detail_y+7, detail_x, self.edit_rgb[1], "G", self.edit_channel_idx==1)
            self.draw_bar(detail_y+8, detail_x, self.edit_rgb[2], "B", self.edit_channel_idx==2)

        elif self.state == 'PRESETS':
            self.stdscr.addstr(detail_y, detail_x, "SELECT PRESET", curses.A_UNDERLINE)
            for idx, name in enumerate(self.preset_list):
                 prefix = "> " if idx == self.preset_idx else "  "
                 attr = curses.A_REVERSE if idx == self.preset_idx else curses.A_NORMAL
                 self.stdscr.addstr(detail_y + 2 + idx, detail_x, f"{prefix}{name}", attr)

        elif self.state == 'FONTS':
            self.stdscr.addstr(detail_y, detail_x, "SELECT FONT", curses.A_UNDERLINE)
            visible_fonts = 10
            start_f = max(0, self.font_idx - visible_fonts // 2)
            end_f = min(len(self.fonts), start_f + visible_fonts)
            for i in range(start_f, end_f):
                idx = i - start_f
                prefix = "> " if i == self.font_idx else "  "
                attr = curses.A_REVERSE if i == self.font_idx else curses.A_NORMAL
                self.stdscr.addstr(detail_y + 2 + idx, detail_x, f"{prefix}{self.fonts[i][:30]}", attr)

        elif self.state == 'CURSOR':
            self.stdscr.addstr(detail_y, detail_x, "CURSOR SETTINGS", curses.A_UNDERLINE)
            
            # Shape
            prefix = "> " if self.cursor_edit_idx == 0 else "  "
            attr = curses.A_BOLD if self.cursor_edit_idx == 0 else curses.A_NORMAL
            self.stdscr.addstr(detail_y + 2, detail_x, f"{prefix}Shape: < {self.cursor_shapes[self.cursor_shape_idx]} >", attr)
            
            # Blink
            prefix = "> " if self.cursor_edit_idx == 1 else "  "
            attr = curses.A_BOLD if self.cursor_edit_idx == 1 else curses.A_NORMAL
            blink_status = "ON" if self.cursor_blink else "OFF"
            self.stdscr.addstr(detail_y + 4, detail_x, f"{prefix}Blink: < {blink_status} >", attr)

        elif self.state == 'INSTALL':
             self.stdscr.addstr(detail_y, detail_x, "PERMANENT INSTALL", curses.A_UNDERLINE)
             self.stdscr.addstr(detail_y+2, detail_x, "This will modify ~/.bashrc")
             self.stdscr.addstr(detail_y+3, detail_x, "Press 'I' to Install")
             self.stdscr.addstr(detail_y+4, detail_x, "Press 'U' to Uninstall")
             self.stdscr.addstr(detail_y+6, detail_x, "Includes Colors, Font, Cursor", curses.A_DIM)

        self.stdscr.addstr(height-2, 2, self.message[:width-4])
        self.stdscr.refresh()

    def save_theme_dialog(self):
        try:
            with open("my_theme.sh", 'w') as f:
                f.write("#!/bin/sh\n")
                for i, c in enumerate(self.colors): f.write(f'echo -en "\\033]P{i:X}{c}"\n')
                if self.current_font != "Default":
                    f.write(f"setfont {self.current_font}\n")
                f.write(f'echo -en "\\033[?{self.cursor_shape_idx}c"\n')
                blink_cmd = "on" if self.cursor_blink else "off"
                f.write(f"setterm --blink {blink_cmd}\n")
                f.write('clear\n')
            self.message = f"Saved to my_theme.sh"
        except Exception as e: self.message = f"Error: {e}"

    def install_permanent(self):
        home = os.path.expanduser("~")
        theme_path = os.path.join(home, ".tty_theme_current.sh")
        bashrc_path = os.path.join(home, ".bashrc")
        
        # 1. Save current theme to hidden file
        try:
            with open(theme_path, 'w') as f:
                f.write("#!/bin/sh\n# Auto-generated TTY theme\n")
                for i, c in enumerate(self.colors): f.write(f'echo -en "\\033]P{i:X}{c}"\n')
                if self.current_font != "Default":
                    f.write(f"setfont {self.current_font}\n")
                f.write(f'echo -en "\\033[?{self.cursor_shape_idx}c"\n')
                blink_cmd = "on" if self.cursor_blink else "off"
                f.write(f"setterm --blink {blink_cmd}\n")
                f.write('clear\n') # clear needed to refresh
            
            # 2. Add to bashrc if not present
            loader_line = f'[ -f "{theme_path}" ] && sh "{theme_path}" # TTY_COLOR_EDITOR_LOADER'
            
            already_in = False
            if os.path.exists(bashrc_path):
                with open(bashrc_path, 'r') as f:
                    if "TTY_COLOR_EDITOR_LOADER" in f.read():
                        already_in = True
            
            if not already_in:
                with open(bashrc_path, 'a') as f:
                    f.write(f"\n{loader_line}\n")
                self.message = "Installed! Theme will load on login."
            else:
                self.message = "Updated theme file (loader was already in bashrc)."
                
        except Exception as e:
            self.message = f"Install failed: {e}"

    def uninstall_permanent(self):
        home = os.path.expanduser("~")
        bashrc_path = os.path.join(home, ".bashrc")
        try:
            if os.path.exists(bashrc_path):
                with open(bashrc_path, 'r') as f: lines = f.readlines()
                with open(bashrc_path, 'w') as f:
                    for line in lines:
                        if "TTY_COLOR_EDITOR_LOADER" not in line:
                            f.write(line)
            self.message = "Uninstalled from .bashrc"
        except Exception as e: self.message = f"Uninstall failed: {e}"

    def load_theme_from_file(self, filename):
        try:
            with open(filename, 'r') as f: content = f.read()
            matches = re.findall(r'\]P([0-9A-Fa-f])([0-9A-Fa-f]{6})', content)
            if matches:
                for idx_char, c in matches:
                    idx = int(idx_char, 16)
                    self.base_colors[idx] = c.upper()
                    self.colors[idx] = c.upper()
                    apply_color(idx, c.upper())
                self.message = f"Loaded {len(matches)} colors. Brightness reset to 1.0."
                self.brightness = 1.0
        except Exception as e: self.message = f"Error: {e}"

def main():
    try:
        def start_app(stdscr):
            app = ColorEditor(stdscr)
            if len(sys.argv) > 1: app.load_theme_from_file(sys.argv[1])
            app.run()
        curses.wrapper(start_app)
    except KeyboardInterrupt: pass
    except Exception as e: print(f"Error: {e}")
            
if __name__ == "__main__":
    main()
