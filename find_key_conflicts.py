import sublime
import sublime_plugin
import os
import json
import threading
import copy
from minify_json import json_minify

PACKAGES_PATH = sublime.packages_path()
PLATFORM = sublime.platform()
MODIFIERS = ('shift', 'ctrl', 'alt', 'super')

DONE_TEXT = "(Done)"
VIEW_SELECTED_LIST_TEXT = "(View Selected)"
VIEW_PACKAGES_LIST_TEXT = "(View Packages)"


class GenerateKeymaps(object):
    def run(self):
        plugin_settings = sublime.load_settings("FindKeyConflicts.sublime-settings")

        self.window = self.window
        self.view = self.window.active_view()
        self.display_internal_conflicts = plugin_settings.get("display_internal_conflicts", True)
        self.show_args = plugin_settings.get("show_args", False)

        packages = self.generate_package_list()

        thread = FindKeyConflictsCall(plugin_settings, packages)
        thread.start()
        self.handle_thread(thread)

    def generate_package_list(self):
        plugin_settings = sublime.load_settings("FindKeyConflicts.sublime-settings")
        view = self.window.active_view()
        packages = [o for o in os.listdir(PACKAGES_PATH) if os.path.isdir(os.path.join(PACKAGES_PATH, o))]
        packages.sort()

        ignored_packages = view.settings().get("ignored_packages", [])
        ignored_packages += plugin_settings.get("ignored_packages", [])

        packages = self.remove_ignored_packages(packages, ignored_packages)
        return packages

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
            if thread.debug:
                content = ""
                for package in thread.debug_minified:
                    content += "%s\n" % package
                    content += "%s\n" % thread.debug_minified[package]

                panel = sublime.active_window().new_file()
                panel.set_scratch(True)
                panel.settings().set('word_wrap', False)
                panel.set_name("Debug")
                panel_edit = panel.begin_edit()
                panel.insert(panel_edit, 0, content)
                panel.end_edit(panel_edit)
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

    def remove_non_conflicts(self, all_key_map):
        keylist = all_key_map.keys()
        keylist.sort()
        new_key_map = {}
        for key in keylist:
            value = all_key_map[key]
            if len(value["packages"]) > 1:
                new_key_map[key] = value
            elif len(value[value["packages"][0]]) > 1 and self.display_internal_conflicts:
                new_key_map[key] = value
        return new_key_map

    def find_overlap_conflicts(self, all_key_map):
        keylist = all_key_map.keys()
        keylist.sort()
        conflicts = {}
        for key in keylist:
            for key_nested in keylist:
                if key_nested.startswith(key + ","):
                    if key in conflicts:
                        conflicts[key].append(key_nested)
                    else:
                        conflicts[key] = [key_nested]
        return conflicts


class GenerateOutput(object):
    def __init__(self, all_key_map, show_args, window=None):
        self.window = window
        self.all_key_map = all_key_map
        self.show_args = show_args

    def generate_header(self, header):
        return '%s\n%s\n%s\n' % ('-' * len(header), header, '-' * len(header))

    def generate_overlapping_key_text(self, conflict_map):
        content = ""
        keys = conflict_map.keys()
        keys.sort()
        potential_conflicts_keys = conflict_map.keys()
        potential_conflicts_keys.sort()
        offset = 2
        for key_string in potential_conflicts_keys:
            content += self.generate_text(key_string, self.all_key_map, 0)
            for conflict in conflict_map[key_string]:
                content += self.generate_text(conflict, self.all_key_map, offset, "(", ")")
        return content

    def generate_key_map_text(self, key_map):
        content = ''
        keys = key_map.keys()

        keys.sort()
        for key_string in keys:
            content += self.generate_text(key_string, key_map)

        return content

    def generate_file(self, content, name="Keys"):
        panel = sublime.active_window().new_file()
        panel.set_scratch(True)
        panel.settings().set('word_wrap', False)
        panel.set_name(name)
        # content output
        panel_edit = panel.begin_edit()
        panel.insert(panel_edit, 0, content)
        panel.end_edit(panel_edit)

    def longest_command_length(self, key_map):
        pass

    def longest_package_length(self, key_map):
        pass

    def generate_text(self, key_string, key_map, offset=0, key_wrap_in='[', key_wrap_out=']'):
        content = ''
        item = key_map.get(key_string)
        content += " " * offset
        content += ' %s%s%s\n' % (key_wrap_in, key_string, key_wrap_out)
        packages = item.get("packages")

        for package in packages:
            package_map = item.get(package)
            for entry in package_map:
                content += " " * offset
                content += '   %*s %*s  %s\n' % \
                    (-40 + offset, entry['command'], -20, package, \
                    json.dumps(entry['context']) if "context" in entry else '')

        return content

    def generate_output_quick_panel(self, key_map):
        self.key_map = key_map
        quick_panel_items = []
        keylist = key_map.keys()
        keylist.sort()
        self.list = []
        for key in keylist:
            self.list.append(key)
            value = key_map[key]
            quick_panel_item = [key, ", ".join(value["packages"])]
            quick_panel_items.append(quick_panel_item)

        self.window.show_quick_panel(quick_panel_items, self.quick_panel_callback)

    def quick_panel_callback(self, index):
        if index == -1:
            return
        entry = self.list[index]
        content = self.generate_header("Entry Details")
        content += self.generate_text(entry, self.key_map)
        self.generate_file(content, "[%s] Details" % entry)


class FindKeyConflictsCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self, output="quick_panel"):
        self.output = output
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args, self.window)

        new_key_map = self.remove_non_conflicts(all_key_map)
        if self.output == "quick_panel":
            output.generate_output_quick_panel(new_key_map)
        elif self.output == "buffer":
            content = output.generate_header("Key Conflicts (Only direct conflicts)")
            content += output.generate_key_map_text(new_key_map)
            output.generate_file(content, "Key Conflicts")
        else:
            print "FindKeyConflicts[Warning]: Invalid output type specified"


class FindAllKeyConflictsCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self):
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args)
        new_key_map = self.remove_non_conflicts(all_key_map)
        overlapping_confilicts_map = self.find_overlap_conflicts(all_key_map)

        content = output.generate_header("Multi Part Key Conflicts")
        content += output.generate_overlapping_key_text(overlapping_confilicts_map)
        content += output.generate_header("Key Conflicts (Only direct conflicts)")
        content += output.generate_key_map_text(new_key_map)
        output.generate_file(content,  "All Key Conflicts")


class FindOverlapConflictsCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self):
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args)
        overlapping_confilicts_map = self.find_overlap_conflicts(all_key_map)

        content = output.generate_header("Multi Part Key Conflicts")
        content += output.generate_overlapping_key_text(overlapping_confilicts_map)
        output.generate_file(content,  "Overlap Key Conflicts")


class FindKeyMappingsCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self, output="quick_panel"):
        self.output = output
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args, self.window)
        if self.output == "quick_panel":
            output.generate_output_quick_panel(all_key_map)
        elif self.output == "buffer":
            content = output.generate_header("All Key Mappings")
            content += output.generate_key_map_text(all_key_map)
            output.generate_file(content, "All Key Mappings")
        else:
            print "FindKeyConflicts[Warning]: Invalid output type specified"


class FindKeyConflictsWithPackageCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self, multiple=False):
        self.package_list = [entry for entry in GenerateKeymaps.generate_package_list(self)]
        self.multiple = multiple
        self.selected_list = []

        self.generate_quick_panel(self.package_list, self.package_list_callback, False)

    def generate_quick_panel(self, packages, callback, selected_list):
        self.quick_panel_list = copy.copy(packages)
        if self.multiple:
            if selected_list:
                self.quick_panel_list.append(VIEW_PACKAGES_LIST_TEXT)
            else:
                self.quick_panel_list.append(VIEW_SELECTED_LIST_TEXT)
            self.quick_panel_list.append(DONE_TEXT)
        self.window.show_quick_panel(self.quick_panel_list, callback)

    def selected_list_callback(self, index):
        if index == -1:
            return

        entry_text = self.quick_panel_list[index]
        if entry_text != VIEW_PACKAGES_LIST_TEXT and entry_text != DONE_TEXT:
            self.package_list.append(entry_text)
            self.selected_list.remove(entry_text)
        self.package_list.sort()

        if entry_text == DONE_TEXT:
            if len(self.selected_list) > 0:
                GenerateKeymaps.run(self)
        elif entry_text == VIEW_PACKAGES_LIST_TEXT:
            self.generate_quick_panel(self.package_list, self.package_list_callback, False)
        else:
            self.generate_quick_panel(self.selected_list, self.selected_list_callback, True)

    def package_list_callback(self, index):
        if index == -1:
            return

        if self.quick_panel_list[index] != DONE_TEXT and self.quick_panel_list[index] != VIEW_SELECTED_LIST_TEXT:
            self.selected_list.append(self.quick_panel_list[index])
            self.package_list.remove(self.quick_panel_list[index])
        self.selected_list.sort()

        if not self.multiple or self.quick_panel_list[index] == DONE_TEXT:
            if len(self.selected_list) > 0:
                GenerateKeymaps.run(self)
        elif self.quick_panel_list[index] == VIEW_SELECTED_LIST_TEXT:
            self.generate_quick_panel(self.selected_list, self.selected_list_callback, True)
        else:
            self.generate_quick_panel(self.package_list, self.package_list_callback, False)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args)

        output_keymap = {}
        overlapping_conflicts_map = {}
        conflict_key_map = self.remove_non_conflicts(all_key_map)
        all_overlapping_confilicts_map = self.find_overlap_conflicts(all_key_map)
        for key in conflict_key_map:
            package_list = conflict_key_map[key]["packages"]
            for package in self.selected_list:
                if package in package_list:
                    output_keymap[key] = conflict_key_map[key]
                    break

        for overlap_base_key in all_overlapping_confilicts_map:
            for package in self.selected_list:
                if package in all_key_map[overlap_base_key]["packages"]:
                    overlapping_conflicts_map[overlap_base_key] = all_overlapping_confilicts_map[overlap_base_key]
                    break

            for overlap_key in all_overlapping_confilicts_map[overlap_base_key]:
                if package in all_key_map[overlap_key]["packages"]:
                    overlapping_conflicts_map[overlap_base_key] = all_overlapping_confilicts_map[overlap_base_key]
                    break

        content = "Key conflicts involving the following packages:\n"
        content += ", ".join(self.selected_list) + "\n\n"

        content += output.generate_header("Multi Part Key Conflicts")
        content += output.generate_overlapping_key_text(overlapping_conflicts_map)
        content += output.generate_header("Key Conflicts")
        content += output.generate_key_map_text(output_keymap)
        output.generate_file(content, "Key Conflicts")


class FindKeyConflictsCall(threading.Thread):
    def __init__(self, settings, packages):
        self.ignore_single_key = settings.get("ignore_single_key", False)
        self.ignore_patterns = settings.get("ignore_patterns", [])
        self.packages = packages
        self.all_key_map = {}
        self.debug_minified = {}
        self.debug = settings.get("debug", False)
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
                    minified_content = json_minify(content)
                    if self.debug:
                        self.debug_minified[package] = minified_content
                    key_map = json.loads(minified_content)
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
                    if "context" in entry:
                        entry["context"].sort()
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
