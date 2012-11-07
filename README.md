# FindKeyConflicts
Assist in finding key conflicts between various plugins. This plugin will report back shortcut keys that are mapped to more than one package. This does not guarantee that the listed plugins are necessarily in conflict, as details, such as scope, are ignored. This is simply a tool to help assist what plugins may be conflicting.

## Usage
This plugin can, by default, only be started through the menu. It is located under `Tools -> Run FindKeyConflicts`. Alternatively, you may define your own keyboard shortcut with the command being `find_key_conflicts`.

## Settings
`ignored_packages`: 

An array containing packages to ignore. Note that the `ignored_packages` in the Preferences are automatically added to this list.