# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2012 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""


import pycam.Plugins
import pycam.Gui.ControlsGTK
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


class ToolpathProcessors(pycam.Plugins.ListPluginBase):

    DEPENDS = ["Toolpaths", "ParameterGroupManager"]
    CATEGORIES = ["Toolpath"]
    UI_FILE = "toolpath_processors.ui"

    def setup(self):
        if self.gui:
            import gtk
            notebook = self.gui.get_object("GCodePrefsNotebook")
            self._pref_items = []
            def clear_preferences():
                for child in notebook.get_children():
                    notebook.remove(child)
                    # we need to clear the whole path down to the "real" item
                    parent = notebook
                    while not child in [entry[0] for entry in self._pref_items]:
                        parent.remove(child)
                        parent = child
                        try:
                            child = child.get_children()[0]
                        except (AttributeError, IndexError):
                            # We encountered an invalid item (e.g. a label
                            # without children) or an empty item.
                            break
                    else:
                        # we found a valid child -> remove it
                        signals = [entry[1] for entry in self._pref_items
                                if child is entry[0]][0]
                        while signals:
                            child.disconnect(signals.pop())
                        parent.remove(child)
            def update_preference_item_visibility(widget, *args):
                """ This function takes care for hiding empty pages of the
                    notebook.
                """
                parent = args[-1]
                if parent is widget:
                    return
                if widget.get_property("visible"):
                    parent.show()
                else:
                    parent.hide()
            def add_preferences_item(item, name):
                matching_entries = [obj for obj in self._pref_items
                        if obj[0] is item]
                if matching_entries:
                    current_entry = matching_entries[0]
                else:
                    current_entry = (item, [])
                    self._pref_items.append(current_entry)
                item.unparent()
                if not isinstance(item, gtk.Frame):
                    # create a simple default frame if none was given
                    frame = gtk.Frame(name)
                    frame.get_label_widget().set_markup("<b>%s</b>" % name)
                    frame.set_shadow_type(gtk.SHADOW_NONE)
                    align = gtk.Alignment()
                    align.set_padding(3, 0, 12, 0)
                    frame.add(align)
                    frame.show()
                    align.add(item)
                    align.show()
                    parent = frame
                else:
                    parent = item
                if not current_entry[1]:
                    for signal in ("hide", "show"):
                        current_entry[1].append(item.connect(signal,
                            update_preference_item_visibility, parent))
                notebook.append_page(parent, gtk.Label(name))
                update_preference_item_visibility(item, parent)
            self.core.register_ui_section("gcode_preferences",
                    add_preferences_item, clear_preferences)
            general_widget = pycam.Gui.ControlsGTK.ParameterSection()
            general_widget.get_widget().show()
            self.core.register_ui_section("gcode_general_parameters",
                    general_widget.add_widget, general_widget.clear_widgets)
            self.core.register_ui("gcode_preferences", "General",
                    general_widget.get_widget())
            self._frame = self.gui.get_object("SettingsFrame")
            self.core.register_ui("toolpath_handling", "Settings", self._frame)
            self.gui.get_object("PreferencesButton").connect("clicked",
                    self._toggle_window, True)
            self.gui.get_object("CloseButton").connect("clicked",
                    self._toggle_window, False)
            self.window = self.gui.get_object("GCodePreferencesWindow")
            self.window.connect("delete-event", self._toggle_window, False)
            self._proc_selector = pycam.Gui.ControlsGTK.InputChoice([],
                    change_handler=lambda widget=None: \
                            self.core.emit_event(
                                "toolpath-processor-selection-changed"))
            proc_widget = self._proc_selector.get_widget()
            self._settings_section = pycam.Gui.ControlsGTK.ParameterSection()
            self._settings_section.get_widget().show()
            self.gui.get_object("SelectorsContainer").add(
                    self._settings_section.get_widget())
            self._settings_section.add_widget(proc_widget,
                    "Toolpath processor", weight=10)
            proc_widget.show()
            self.core.get("register_parameter_group")("toolpath_processor",
                    changed_set_event="toolpath-processor-selection-changed",
                    changed_set_list_event="toolpath-processor-list-changed",
                    get_current_set_func=self.get_selected)
            self._event_handlers = (
                    ("toolpath-processor-list-changed", self._update_processors),
                    ("toolpath-selection-changed", self._update_visibility),
            )
            self.register_event_handlers(self._event_handlers)
            self._update_processors()
            self._update_visibility()
        return True

    def teardown(self):
        if self.gui:
            self._toggle_window(False)
        self.unregister_event_handlers(self._event_handlers)
        self.core.get("unregister_parameter_group")("toolpath_processor")

    def get_selected(self):
        all_processors = self.core.get("get_parameter_sets")("toolpath_processor")
        current_name = self._proc_selector.get_value()
        return all_processors.get(current_name, None)

    def select(self, item=None):
        if not item is None:
            item = item["name"]
        self._proc_selector.set_value(item)

    def _update_visibility(self):
        if self.core.get("toolpaths").get_selected():
            self._frame.show()
        else:
            self._frame.hide()

    def _update_processors(self):
        selected = self.get_selected()
        processors = self.core.get("get_parameter_sets")("toolpath_processor").values()
        processors.sort(key=lambda item: item["weight"])
        choices = []
        for processor in processors:
            choices.append((processor["label"], processor["name"]))
        self._proc_selector.update_choices(choices)
        if selected:
            self.select(selected)
        elif len(processors) > 0:
            self.select(None)
        else:
            pass

    def _toggle_window(self, *args):
        status = args[-1]
        if status:
            self.window.show()
        else:
            self.window.hide()
        # don't destroy the window
        return True


class ToolpathProcessorMilling(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "GCodeSafetyHeight", "GCodeFilenameExtension",
            "GCodeStepWidth", "GCodeSpindle", "GCodeCornerStyle"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        parameters = {"safety_height": 25,
                "filename_extension": "",
                "step_width_x": 0.0001,
                "step_width_y": 0.0001,
                "step_width_z": 0.0001,
                "path_mode": "exact_path",
                "motion_tolerance": 0.0,
                "naive_tolerance": 0.0,
                "spindle_enable": True,
                "spindle_delay": 3,
        }
        self.core.get("register_parameter_set")("toolpath_processor",
                "milling", "Milling", self.get_filters, parameters=parameters,
                weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_processor", 
                "milling")

    def get_filters(self):
        return []


class ToolpathProcessorLaser(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "GCodeFilenameExtension", "GCodeStepWidth",
            "GCodeCornerStyle"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        parameters = {"filename_extension": "",
                "step_width_x": 0.0001,
                "step_width_y": 0.0001,
                "step_width_z": 0.0001,
                "path_mode": "exact_path",
                "motion_tolerance": 0.0,
                "naive_tolerance": 0.0,
        }
        self.core.get("register_parameter_set")("toolpath_processor",
                "laser", "Laser", self.get_filters, parameters=parameters,
                weight=50)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_processor",
                "laser")

    def get_filters(self):
        return []
