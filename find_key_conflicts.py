# handle Default.sublime-keymap (applies to all platforms)
import sublime
import sublime_plugin
import os
import json
from minify_json import *

PACKAGES_PATH = sublime.packages_path()
PLATFORM = sublime.platform()


class FindKeyConflictsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.all_key_map = {}
        if PLATFORM == "windows":
            self.type = "Windows"
        elif PLATFORM == "linux":
            self.type = "Linux"
        else:
            self.type = "OSX"
        packages = os.listdir(PACKAGES_PATH)
        packages.sort()
        self.check_for_conflicts("Default")
        preferences = sublime.load_settings("Preferences.sublime-settings")
        ignored_packages = preferences.get("ignored_packages", [])
        for package in packages:
            if package == "Default" or package == "User" or package in ignored_packages:
                continue
            self.check_for_conflicts(package)
        self.check_for_conflicts("User")

        for key, value in self.all_key_map.iteritems():
            if len(value) > 1:
                print key
                print value

    def check_for_conflicts(self, package):
        path = os.path.join(PACKAGES_PATH, package)
        end_extension = "(" + self.type + ").sublime-keymap"

        for filename in os.listdir(path):
            if filename.endswith(end_extension):

                path = os.path.join(path, filename)

                key_map = json.loads(json_minify(open(path).read()))
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
