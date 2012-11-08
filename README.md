# FindKeyConflicts
Assist in finding key conflicts between various plugins. This plugin will report back shortcut keys that are mapped to more than one package. This does not guarantee that the listed plugins are necessarily in conflict, as details, such as scope, are ignored. This is simply a tool to help assist what plugins may be conflicting.

## Installation
Clone or copy this repository into the packages directory. By default, they are located at:

* OS X: ~/Library/Application Support/Sublime Text 2/Packages/
* Windows: %APPDATA%/Roaming/Sublime Text 2/Packages/
* Linux: ~/.config/sublime-text-2/Packages/

## Usage
This plugin can be run through specifying commands on the command palete. The commands are listed in alphabetical order, beginning with modifiers (alt, cntl, shift, super), followed by keys. The commands are as follows:

`FindKeyConflicts: Conflicts to Quick Panel`:

This command finds all key conflicts, and displays them on the quick panel. The last package listed under the command is the source for the command being run.

`FindKeyConflicts: Conflicts to Buffer`:

Display key conflicts in a view. Using this will give a better idea of how commands conflict, as the context for the commands will be included in the output.

`FindKeyConflicts: All Mappings to Buffer`:

Displays all key mappings in a buffer.

## Settings
`ignored_packages`: 

An array containing packages to ignore. Note that the `ignored_packages` in the Preferences are automatically added to this list.

`ignore_single_key`:

Boolean value specifying if single key bindings should be ignored. False by default.

`ignore_patterns`:

Array containing key patterns to ignore. These should follow the same guidelines as specifying key bindings.

## Notes
Thanks to [bizoo](https://github.com/bizoo) for sharing his work with me.