import sublime
import sublime_plugin
import os
import json
from minify_json import json_minify
import threading

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
        plugin_settings = sublime.load_settings("FindKeyConflicts.sublime-settings")

        ignored_packages = preferences.get("ignored_packages", [])
        ignored_packages += plugin_settings.get("ignored_packages", [])
        plugin_settings.set("type", self.type)

        packages = self.remove_ignored_packages(packages, ignored_packages)
        thread = FindKeyConflictsCall(plugin_settings, packages)
        thread.start()
        self.handle_thread(thread)

    def handle_thread(self, thread, i=0, move=1):
        if thread.is_alive():
            # This animates a little activity indicator in the status area
            before = i % 8
            after = (7) - before
            if not after:
                move = -1
            if not before:
                move = 1
            i += move
            self.view.set_status('find_key_conflicts', 'FindKeyConflicts [%s=%s]' % \
                (' ' * before, ' ' * after))

            # Timer to check again.
            sublime.set_timeout(lambda: self.handle_thread(thread, i, move), 100)
        else:
            self.view.erase_status('find_key_conflicts')
            sublime.status_message('FindKeyConflicts finished.')

            self.show_popup(thread.all_key_map)

    def show_popup(self, all_key_map):
        quick_panel_items = []
        for key, value in all_key_map.iteritems():
            if len(value) > 1:
                quick_panel_item = [key, ", ".join(value)]
                quick_panel_items.append(quick_panel_item)

        self.window.show_quick_panel(quick_panel_items, self.quick_panel_callback)

    def remove_ignored_packages(self, packages, ignored_packages):
        for ignored_package in ignored_packages:
            try:
                packages.remove(ignored_package)
            except:
                print "FindKeyConflicts: Package '" + ignored_package + "' does not exist."

        return packages


class FindKeyConflictsCall(threading.Thread):
    def __init__(self, settings, packages):
        self.platform_type = settings.get("type")
        self.ignore_single_key = settings.get("ignore_single_key", True)
        self.ignore_patterns = settings.get("ignore_patterns", [])
        self.packages = packages
        self.all_key_map = {}
        self.prev_error = False
        threading.Thread.__init__(self)

    def run(self):
        run_user = False
        temp = []
        for ignore_pattern in self.ignore_patterns:
            temp.append(self.order_key_string(ignore_pattern))
        self.ignore_patterns = temp
        if "Default" in self.packages:
            self.check_for_conflicts("Default")
            self.packages.remove("Default")
        if "User" in self.packages:
            run_user = True
            self.packages.remove("User")

        for package in self.packages:
            self.check_for_conflicts(package)
        if run_user:
            self.check_for_conflicts("User")

    def check_for_conflicts(self, package):
        orig_path = os.path.join(PACKAGES_PATH, package)
        end_extension = ".sublime-keymap"
        self.done = False

        for filename in os.listdir(orig_path):
            if filename.startswith("Default") and filename.endswith(end_extension):
                if "(" + self.platform_type + ")" in filename or ("(" not in filename and ")" not in filename):
                    path = os.path.join(orig_path, filename)

                    content = open(path).read()
                    try:
                        key_map = json.loads(content)
                    except:
                        try:
                            key_map = json.loads(json_minify(content))
                        except:
                            if not self.prev_error:
                                self.prev_error = True
                                sublime.error_message("Could not parse a keymap file. See console for details")

                            error_path = os.path.join(os.path.basename(orig_path), filename)
                            print "FindKeyConflicts[Warning]: An error " + \
                                  "occured while parsing '" + error_path + "'"
                            continue

                    for entry in key_map:
                        keys = entry["keys"]

                        key_array = []
                        key_string = ""
                        for key in keys:
                            key_array.append(self.order_key_string(key))

                        if self.check_ignore(key_array):
                            continue
                        key_string = ",".join(key_array)

                        if key_string in self.all_key_map:
                            tmp = self.all_key_map.get(key_string)
                            if package not in tmp:
                                tmp.append(package)
                            self.all_key_map[key_string] = tmp
                        else:
                            self.all_key_map[key_string] = [package]
        self.done = True

        return

    def check_ignore(self, key_array):

        if ",".join(key_array) in self.ignore_patterns:
            return True
        if len(key_array) > 1 or not self.ignore_single_key:
            return False

        for key_string in key_array:
            split_keys = key_string.split("+")
            try:
                i = split_keys.index("")
                split_keys[i] = "+"
                split_keys.remove("")
            except:
                pass

            if len(split_keys) == 1 and self.ignore_single_key:
                return True

        return False

    def order_key_string(self, key_string):
        split_keys = key_string.split("+")
        try:
            i = split_keys.index("")
            split_keys[i] = "+"
            split_keys.remove("")
        except:
            pass

        split_keys.sort()
        ordered_key_string = "+".join(split_keys)
        return ordered_key_string
