# Threading
# Additional ignore packages
# Ignore key patterns
# Ignore single key commands
# Split output in quick panel
import sublime
import sublime_plugin
import os
import json
from minify_json import json_minify

PACKAGES_PATH = sublime.packages_path()
PLATFORM = sublime.platform()


class FindKeyConflictsCommand(sublime_plugin.TextCommand):
    def quick_panel_callback(self, index):
        pass

    def run(self, edit):
        self.all_key_map = {}
        self.window = self.view.window()
        if PLATFORM == "windows":
            self.type = "Windows"
        elif PLATFORM == "linux":
            self.type = "Linux"
        else:
            self.type = "OSX"

        packages = os.listdir(PACKAGES_PATH)
        packages.sort()

        preferences = sublime.load_settings("Preferences.sublime-settings")
        ignored_packages = preferences.get("ignored_packages", [])

        self.check_for_conflicts("Default")
        for package in packages:
            if package == "Default" or package == "User" or package in ignored_packages:
                continue
            self.check_for_conflicts(package)
        self.check_for_conflicts("User")

        quick_panel_items = []
        for key, value in self.all_key_map.iteritems():
            if len(value) > 1:
                quick_panel_item = [key, ", ".join(value)]
                quick_panel_items.append(quick_panel_item)

        self.window.show_quick_panel(quick_panel_items, self.quick_panel_callback)

    def check_for_conflicts(self, package):
        path = os.path.join(PACKAGES_PATH, package)
        end_extension = ".sublime-keymap"

        for filename in os.listdir(path):
            if filename.startswith("Default") and filename.endswith(end_extension):
                if "(" + self.type + ")" in filename or ("(" not in filename and ")" not in filename):
                    path = os.path.join(path, filename)

                    content = open(path).read()
                    try:
                        key_map = json.loads(content)
                    except:
                        key_map = json.loads(json_minify(content))

                    for entry in key_map:
                        keys = entry["keys"]

                        key_string = ""
                        for key in keys:
                            tmp_key_string = self.order_key_string(key)
                            key_string += tmp_key_string + ","
                        key_string = key_string[0:-1]
                        if key_string in self.all_key_map:
                            tmp = self.all_key_map.get(key_string)
                            if package not in tmp:
                                tmp.append(package)
                            self.all_key_map[key_string] = tmp
                        else:
                            self.all_key_map[key_string] = [package]

    def order_key_string(self, key_string):
        split_keys = key_string.split("+")
        split_keys.sort()
        ordered_key_string = "+".join(split_keys)
        return ordered_key_string
