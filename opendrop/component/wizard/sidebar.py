from typing import MutableMapping, Optional

from gi.repository import Gtk, Gdk, GObject

from opendrop.component.wizard.wizard import WizardPositionView, WizardPageID
from opendrop.component.gtk_widget_view import GtkWidgetView
from opendrop.utility.bindable.bindable import AtomicBindableAdapter


class SidebarWizardPositionView(WizardPositionView, GtkWidgetView[Gtk.Box]):
    STYLE = '''
    .wizard-sidebar {
        background-color: GAINSBORO;
        border-right: 1px solid SILVER;
        padding: 15px;
    }
    '''

    _STYLE_PROV = Gtk.CssProvider()
    _STYLE_PROV.load_from_data(bytes(STYLE, 'utf-8'))
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), _STYLE_PROV, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def __init__(self):
        self._active_key = None  # type: Optional[WizardPageID]
        self._key_to_lbl = {}  # type: MutableMapping[WizardPageID, Gtk.Label]
        self.bn_active_key = AtomicBindableAdapter(setter=self._set_active_key)

        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15, vexpand=True)
        self.widget.get_style_context().add_class('wizard-sidebar')
        self.widget.show_all()

    def add_key(self, key: WizardPageID) -> None:
        lbl = self._new_label(key.title)
        lbl.show()
        self.widget.add(lbl)
        self._key_to_lbl[key] = lbl

    def clear(self) -> None:
        for lbl in self._key_to_lbl.values():
            lbl.destroy()

        self._key_to_lbl = {}
        self._active_key = None

    def _set_active_key(self, key: Optional[WizardPageID]) -> None:
        old_key = self._active_key

        if old_key is not None:
            old_lbl = self._key_to_lbl[old_key]
            self._format_label_inactive(old_lbl, old_key.title)

        if key is not None:
            lbl = self._key_to_lbl[key]
            self._format_label_active(lbl, key.title)

        self._active_key = key

    # todo: the next three methods are not very object oriented.
    def _new_label(self, title: str) -> Gtk.Widget:
        lbl = Gtk.Label(label=title, xalign=0)

        # Set the size request of the label to its maximum possible size when inactive/active, this should stop the
        # sidebar from resizing its width when the largest child label becomes inactive/active.
        self._format_label_active(lbl, title)
        max_width = lbl.get_layout().get_size().width/1000
        self._format_label_inactive(lbl, title)
        max_width = max(max_width, lbl.get_layout().get_size().width/1000)

        lbl.set_size_request(int(max_width + 1), -1)

        return lbl

    @staticmethod
    def _format_label_active(lbl: Gtk.Label, title: str) -> None:
        lbl.set_markup('<b>{}</b>'.format(GObject.markup_escape_text(title)))

    @staticmethod
    def _format_label_inactive(lbl: Gtk.Label, title: str) -> None:
        lbl.set_markup(GObject.markup_escape_text(title))