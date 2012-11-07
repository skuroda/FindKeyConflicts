# FindKeyConflicts
Assist in finding key conflicts between various plugins. This plugin will report back shortcut keys that are mapped to more than one package. This does not guarantee that the listed plugins are necessarily in conflict, as details, such as scope, are ignored. This is simply a tool to help assist what plugins may be conflicting.

## Installation
Clone or copy this repository into the packages directory. By default, they are located at:

* OS X: ~/Library/Application Support/Sublime Text 2/Packages/
* Windows: %APPDATA%/Roaming/Sublime Text 2/Packages/
* Linux: ~/.config/sublime-text-2/Packages/

## Usage
This plugin can, by default, only be started through the menu. It is located under `Tools -> Run FindKeyConflicts`. Alternatively, you may define your own keyboard shortcut with the command being `find_key_conflicts`. Only keybindings that are conflicting are shown. The last package in the list is the source of the command being used. Note that the keybindings are displayed in alphabetical order. If you are searching for a particular pattern, insert the commands to search for accordingly.

## Settings
`ignored_packages`: 

An array containing packages to ignore. Note that the `ignored_packages` in the Preferences are automatically added to this list.

`ignore_single_key`:

Boolean value specifying if single key bindings should be ignored. False by default.

`ignore_patterns`:

Array containing key patterns to ignore. These should follow the same guidelines as specifying key bindings.