import sublime
import sublime_plugin
import os
import json
from minify_json import json_minify
import threading

PACKAGES_PATH = sublime.packages_path()
PLATFORM = sublime.platform()
MODIFIERS = ('shift', 'ctrl', 'alt', 'super')


class GenerateKeymaps(object):
    def run(self):
        self.all_key_map = {}
        self.window = self.window
        self.view = self.window.active_view()

        packages = os.listdir(PACKAGES_PATH)
        packages.sort()

        plugin_settings = sublime.load_settings("FindKeyConflicts.sublime-settings")

        ignored_packages = self.view.settings().get("ignored_packages", [])
        ignored_packages += plugin_settings.get("ignored_packages", [])

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

            self.handle_results(thread.all_key_map)

    def handle_results(self, all_key_map):
        raise NotImplementedError("Should have implemented this")

    def remove_ignored_packages(self, packages, ignored_packages):
        for ignored_package in ignored_packages:
            try:
                packages.remove(ignored_package)
            except:
                print "FindKeyConflicts: Package '" + ignored_package + "' does not exist."

        return packages


class GenerateOutput(object):
    def generate_file(self, all_key_map):
        txt = ''
        keys = all_key_map.keys()
        keys.sort()
        for key_string in keys:
            txt += self.generate_text(key_string, all_key_map)

        panel = sublime.active_window().new_file()
        panel.set_scratch(True)
        panel.settings().set('word_wrap', False)
        # content output
        panel_edit = panel.begin_edit()
        panel.insert(panel_edit, 0, txt)
        panel.end_edit(panel_edit)

    def generate_text(self, key_string, all_key_map, offset=0):
        txt = ''
        item = all_key_map.get(key_string)
        txt += " " * offset
        txt += ' [%s]\n' % (key_string)
        packages = item.get("packages")

        for package in packages:
            package_map = item.get(package)
            for entry in package_map:
                txt += " " * offset
                txt += '   %-40s %-20s  %s\n' % \
                (entry['command'], package, entry['context'] if "context" in entry else '')

        return txt

    def generate_quickpanel(self, all_key_map):
        quick_panel_items = []
        keylist = all_key_map.keys()
        keylist.sort()
        for key in keylist:
            value = all_key_map[key]
            quick_panel_item = [key, ", ".join(value["packages"])]
            quick_panel_items.append(quick_panel_item)

        self.window.show_quick_panel(quick_panel_items, self.quick_panel_callback)

    def quick_panel_callback(self, index):
        pass


class FindKeyConflictsCommand(GenerateKeymaps, GenerateOutput, sublime_plugin.WindowCommand):
    def run(self, output="quick_panel"):
        self.output = output
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        if self.output == "quick_panel":
            self.generate_quickpanel(all_key_map)
        elif self.output == "buffer":
            self.generate_file(all_key_map)
        else:
            print "FindKeyConflicts[Warning]: Invalid output type specified"

    def generate_file(self, all_key_map):
        keylist = all_key_map.keys()
        keylist.sort()
        new_key_map = {}
        for key in keylist:
            value = all_key_map[key]
            if len(value["packages"]) > 1:
                new_key_map[key] = value
        GenerateOutput.generate_file(self, new_key_map)

    def generate_quickpanel(self, all_key_map):
        keylist = all_key_map.keys()
        keylist.sort()
        new_key_map = {}
        for key in keylist:
            value = all_key_map[key]
            if len(value["packages"]) > 1:
                new_key_map[key] = value
        GenerateOutput.generate_quickpanel(self, new_key_map)


class FindKeyMappingsCommand(GenerateKeymaps, GenerateOutput, sublime_plugin.WindowCommand):
    def run(self):
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        self.generate_file(all_key_map)


class FindKeyConflictsCall(threading.Thread):
    def __init__(self, settings, packages):
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
        self.done = False

        for filename in os.listdir(orig_path):
            if filename.lower() == "default.sublime-keymap" or \
            filename.lower() == "default (%s).sublime-keymap" % (PLATFORM.lower()):
                path = os.path.join(orig_path, filename)

                content = open(path).read()
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
                        if package not in tmp["packages"]:
                            tmp["packages"].append(package)
                            tmp[package] = [entry]
                        else:
                            tmp[package].append(entry)

                        self.all_key_map[key_string] = tmp
                    else:
                        new_entry = {}
                        new_entry["packages"] = [package]
                        new_entry[package] = [entry]
                        self.all_key_map[key_string] = new_entry
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

        modifiers = []
        keys = []
        for key in split_keys:
            if key in MODIFIERS:
                modifiers.append(key)
            else:
                keys.append(key)
        modifiers.sort()
        keys.sort()
        ordered_key_string = "+".join(modifiers + keys)
        return ordered_key_string
